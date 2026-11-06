import unittest
from monn.lexer import Lexer
from monn.parser import Parser
from monn.errors import MonnSyntaxError
from monn.web import compile_to_html

class LexerParserTests(unittest.TestCase):
    def test_tokenizes_window_and_label(self):
        tokens=Lexer().tokenize("...\n..... 'سلام'")
        self.assertEqual([t.op for t in tokens],["CREATE_WINDOW","CREATE_LABEL"])
        self.assertEqual(tokens[1].params["t"],"سلام")
    def test_counted_loop_builds_children(self):
        tree=Parser(Lexer().tokenize("......[3\n..... 'hi'\n......]")).parse()
        self.assertEqual(tree.children[0].op,"LOOP_COUNT")
        self.assertEqual(len(tree.children[0].children),1)
    def test_persian_loop_alias(self):
        tree=Parser(Lexer().tokenize("تکرار 4\nمتن سلام\nپایان حلقه")).parse()
        self.assertEqual(tree.children[0].op,"LOOP_COUNT")
        self.assertEqual(tree.children[0].params["n"],4)
    def test_if_else_is_nested(self):
        src="اگر 3 > 2\nمتن درست\nوگرنه\nمتن غلط\nپایان"
        node=Parser(Lexer().tokenize(src)).parse().children[0]
        self.assertEqual(node.op,"IF_START")
        self.assertEqual(len(node.children),1)
        self.assertEqual(len(node.alternate),1)
    def test_shorthand_if_defaults_true(self):
        node=Parser(Lexer().tokenize("????\n..... 'ok'\n?????")).parse().children[0]
        self.assertEqual(node.params,{})
    def test_rejects_else_outside_if(self):
        with self.assertRaises(MonnSyntaxError): Parser(Lexer().tokenize("وگرنه")).parse()
    def test_unknown_command_raises(self):
        with self.assertRaises(MonnSyntaxError): Lexer().tokenize("not a monn command")
    def test_unclosed_block_raises(self):
        with self.assertRaises(MonnSyntaxError): Parser(Lexer().tokenize("......[3")).parse()
    def test_web_export_is_standalone(self):
        html=compile_to_html("متن سلام\nدکمه شروع")
        self.assertIn("<!doctype html>",html.lower())
        self.assertIn("سلام",html)
        self.assertIn("شروع",html)
if __name__=="__main__": unittest.main()
