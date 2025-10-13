import unittest
import os
from main import generate_word, generate_word_frequencies, generate_random_names, save_word_frequencies_to_csv

class TestWordleFunctions(unittest.TestCase):
    def test_generate_word_length(self):
        word = generate_word(5)
        self.assertEqual(len(word), 5)
        self.assertTrue(word.islower())
        self.assertTrue(word.isalpha())

    def test_generate_word_frequencies(self):
        freq_dict = generate_word_frequencies(num_words=10, max_frequency=50)
        self.assertEqual(len(freq_dict), 10)
        for freq in freq_dict.values():
            self.assertTrue(1 <= freq <= 50)

    def test_generate_random_names(self):
        names = generate_random_names(num_names=20, name_length=5)
        self.assertEqual(len(names), 20)
        for name in names:
            self.assertEqual(len(name), 5)
            self.assertTrue(name.islower())
            self.assertTrue(name.isalpha())

    def test_save_word_frequencies_to_csv(self):
        test_dict = {'apple': 10, 'berry': 20}
        filename = 'test_word_freq.csv'
        save_word_frequencies_to_csv(test_dict, filename)
        self.assertTrue(os.path.exists(os.path.join(os.getcwd(), filename)))
        # Clean up
        os.remove(os.path.join(os.getcwd(), filename))

if __name__ == "__main__":
    unittest.main()
