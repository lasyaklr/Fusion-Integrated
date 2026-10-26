import inspect

from modules.elm import contracts


def test_contracts_plural_signatures():
    for name, func in inspect.getmembers(contracts, inspect.isfunction):
        if name.startswith("get_"):
            sig = inspect.signature(func)
            param = next(iter(sig.parameters.values()))
            # Ensure first parameter is a Sequence
            assert "Sequence" in str(param.annotation) or "list" in str(param.annotation)
