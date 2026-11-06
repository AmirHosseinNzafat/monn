import unittest

from monn.lexer import Lexer
from monn.commands import COMMANDS
from monn.parser import Parser


class MonnFeatureSyntaxTests(unittest.TestCase):
    def test_new_style_commands_are_registered(self):
        for source in (
            "##color", "##padding:8", "##relief:groove",
            "##cursor:hand2", "##alpha:0.9", "##resizable:1",
            "...theme:dark",
        ):
            with self.subTest(source=source):
                self.assertIsNotNone(Lexer()._match_line(source, 1))

    def test_new_ui_commands_are_registered(self):
        for source in (
            "..tabs", "..list", "..combo", "..slider", "..progress",
            "..menu", "..chat", "..image:a blue bird",
            "..create3d:cube", "..ask:your name",
        ):
            with self.subTest(source=source):
                self.assertIsNotNone(Lexer()._match_line(source, 1))

    def test_color_picker_token_has_expected_operation(self):
        token = Lexer().tokenize("##color")[0]
        self.assertEqual(token.op, "CHOOSE_COLOR")

    def test_image_prompt_is_preserved(self):
        token = Lexer().tokenize("..image:a quiet forest at dawn")[0]
        self.assertEqual(token.params["prompt"], "a quiet forest at dawn")

    def test_counted_loop_and_new_commands_parse(self):
        tree = Parser(Lexer().tokenize("......[2\n..tabs\n......]")).parse()
        self.assertEqual(tree.children[0].op, "LOOP_COUNT")
        self.assertEqual(tree.children[0].children[0].op, "CREATE_TABS")


if __name__ == "__main__":
    unittest.main()
