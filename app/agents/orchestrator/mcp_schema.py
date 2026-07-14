import json
import logging
from typing import Any, Optional
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)


class EmptySchema(BaseModel):
    pass


class MCPSchemaTranslator:
    @staticmethod
    def extract_message(output: Any) -> str:
        if isinstance(output, str):
            try:
                parsed = json.loads(output)
                return parsed.get("message") or parsed.get("answer") or output
            except json.JSONDecodeError:
                return output

        if isinstance(output, dict):
            return (
                output.get("message")
                or output.get("answer")
                or output.get("query")
                or json.dumps(output, ensure_ascii=False)
            )

        return str(output)

    @staticmethod
    def json_schema_to_pydantic_fields(schema: dict) -> dict:
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        fields = {}

        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }

        for name, prop in properties.items():
            type_str = prop.get("type", "string")
            description = prop.get("description", "")
            py_type = type_mapping.get(type_str, Any)

            if name in required:
                fields[name] = (py_type, Field(description=description))
            else:
                fields[name] = (
                    Optional[py_type],
                    Field(default=None, description=description),
                )

        return fields
