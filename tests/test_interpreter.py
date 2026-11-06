import unittest

from monn.lexer import Lexer
from monn.parser import Parser
from monn.errors import MonnSyntaxError


class LexerParserTests(unittest.TestCase):
    def test_tokenizes_window_and_label(self):
        tokens = Lexer().tokenize("...\n..... 'سلام'")
        self.assertEqual([token.op for token in tokens], ["CREATE_WINDOW", "CREATE_LABEL"])
        self.assertEqual(tokens[1].params["t"], "سلام")

    def test_counted_loop_builds_children(self):
        tree = Parser(Lexer().tokenize("......[3\n..... 'hi'\n......]")).parse()
        loop = tree.children[0]
        self.assertEqual(loop.op, "LOOP_COUNT")
        self.assertEqual(len(loop.children), 1)

    def test_unknown_command_raises_syntax_error(self):
        with self.assertRaises(MonnSyntaxError):
            Lexer().tokenize("not a monn command")

    def test_unclosed_block_raises_syntax_error(self):
        with self.assertRaises(MonnSyntaxError):
            Parser(Lexer().tokenize("......[3")).parse()


if __name__ == "__main__":
    unittest.main()
