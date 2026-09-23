"""Base tool interfaces, schema definitions, and registry for locaLLM."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Iterable, List, Optional, Set


class BaseTool(ABC):
    """Abstract base class for all callable tools."""

    name: str
    description: str
    parameters: Dict[str, Any]
    is_mutating: bool = False
    categories: Set[str] = {"assistant"}

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        is_mutating: bool = False,
        categories: Optional[Iterable[str]] = None,
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters or {"type": "object", "properties": {}}
        self.is_mutating = is_mutating
        self.categories = set(categories) if categories else {"assistant"}

    @abstractmethod
    def execute(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Execute the tool logic with provided arguments and optional execution context."""
        pass

    def to_schema(self) -> Dict[str, Any]:
        """Convert tool declaration into OpenAI/Ollama function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class FunctionTool(BaseTool):
    """Tool implementation wrapping a standalone Python callable."""

    def __init__(
        self,
        name: str,
        description: str,
        fn: Callable[..., str],
        parameters: Optional[Dict[str, Any]] = None,
        is_mutating: bool = False,
        categories: Optional[Iterable[str]] = None,
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            parameters=parameters,
            is_mutating=is_mutating,
            categories=categories,
        )
        self._fn = fn

    def execute(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Call underlying function, forwarding context and boundary parameters if accepted."""
        import inspect

        sig = inspect.signature(self._fn)
        kwargs = dict(arguments)

        if "context" in sig.parameters:
            kwargs["context"] = context
        if "boundary_dir" in sig.parameters and context and "boundary_dir" in context:
            kwargs["boundary_dir"] = context["boundary_dir"]

        has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        if not has_var_keyword:
            kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}

        return self._fn(**kwargs)


class ToolRegistry:
    """Central registry maintaining discovered and loaded tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool_instance: BaseTool) -> BaseTool:
        """Register a tool instance into the registry."""
        self._tools[tool_instance.name] = tool_instance
        return tool_instance

    def get(self, name: str) -> Optional[BaseTool]:
        """Lookup tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Return list of all registered tools."""
        return list(self._tools.values())

    def get_schemas(self, category: str = "assistant") -> List[Dict[str, Any]]:
        """Return function calling schemas for a specific category."""
        schemas: List[Dict[str, Any]] = []
        for t in self._tools.values():
            if category == "all" or category in t.categories:
                schemas.append(t.to_schema())
        return schemas

    def get_mutating_tool_names(self) -> Set[str]:
        """Return names of all tools registered as mutating."""
        return {name for name, t in self._tools.items() if t.is_mutating}


# Global tool registry singleton
registry = ToolRegistry()


def tool(
    name: str,
    description: str,
    parameters: Optional[Dict[str, Any]] = None,
    is_mutating: bool = False,
    categories: Optional[Iterable[str]] = None,
    reg: Optional[ToolRegistry] = None,
) -> Callable[[Callable[..., str]], FunctionTool]:
    """Decorator to register a function as a tool in the registry."""
    target_registry = reg or registry

    def decorator(fn: Callable[..., str]) -> FunctionTool:
        ft = FunctionTool(
            name=name,
            description=description,
            fn=fn,
            parameters=parameters,
            is_mutating=is_mutating,
            categories=categories,
        )
        target_registry.register(ft)
        return ft

    return decorator
