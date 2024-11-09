# test_google_api_interface.py

import unittest
from modules.google_api_interface import ContentGenerator

class TestContentGenerator(unittest.TestCase):

    def setUp(self):
        self.content_generator = ContentGenerator()

    def test_initialization(self):
        self.assertIsNotNone(self.content_generator)
        self.assertEqual(self.content_generator.model_name, 'gemini-1.5-flash-002')

    def test_default_safety_settings(self):
        safety_settings = self.content_generator.default_safety_settings()
        self.assertEqual(len(safety_settings), 4)
        # Add more specific assertions about safety settings if needed

    def test_generate_content(self):
        test_prompt = "Write a brief summary of the American Revolution."
        result = self.content_generator.generate_content(test_prompt)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        # Add more assertions to check the quality of the generated content

if __name__ == '__main__':
    unittest.main()