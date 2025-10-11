
## Wordle Project

This project generates word frequency data, processes real names, and includes a simple guessing game based on random names.

### Features
- Generate random words and assign frequencies
- Save word-frequency data to CSV files
- Read real names from a file and save names of length 5 to a CSV file
- Play a guessing game:
  - Generates 1000 random names (length 5)
  - Prompts the user for 6 names (length 5)
  - Computer selects 5 random names from the generated list
  - User has 3 attempts to guess any of the computer's selected names
  - Prints "win" if guessed correctly, otherwise "lose"

### Usage
1. (Optional) Place a file named `names.txt` in the project directory, with one real name per line, if you want to use the real names CSV feature.
2. To play the game, simply run:
	```bash
	python src/main.py
	```
3. Follow the prompts in the terminal to play the guessing game.
4. The script can also generate CSV files such as `word_frequencies.csv`, `random_words.csv`, or `real_names.csv` depending on the function called.

### Requirements
No external dependencies required for basic functionality. All modules used are part of Python's standard library.
