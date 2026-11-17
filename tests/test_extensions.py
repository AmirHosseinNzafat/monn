import unittest
from unittest.mock import patch

from monn.extensions import ExtensionError, ExtensionRegistry, load_extension


class FakeEntry:
    name = "sample"
    value = "sample:register"

    def load(self):
        def register(registry):
            registry.register_tool("hello", lambda: "hello", "sample tool")
        return register


class ExtensionTests(unittest.TestCase):
    def test_extension_requires_explicit_approval(self):
        with patch("monn.extensions._entry_points", return_value=[FakeEntry()]):
            with self.assertRaises(ExtensionError):
                load_extension("sample")

    def test_approved_extension_registers_tool(self):
        with patch("monn.extensions._entry_points", return_value=[FakeEntry()]):
            registry = load_extension("sample", approved=True)
        self.assertEqual(registry.tools["hello"]["callback"](), "hello")

    def test_registry_rejects_duplicate_tool_names(self):
        registry = ExtensionRegistry()
        registry.register_tool("hello", lambda: None)
        with self.assertRaises(ExtensionError):
            registry.register_tool("hello", lambda: None)


if __name__ == "__main__":
    unittest.main()
