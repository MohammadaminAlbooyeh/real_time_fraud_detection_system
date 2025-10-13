

## Wordle Project

This project generates word frequency data, processes real names, and includes a simple guessing game based on random names.

---

### Features

- **Generate random words and assign frequencies**
  - Create a dictionary of random words (length 5) and assign each a random frequency.
- **Save word-frequency data to CSV files**
  - Export generated word-frequency dictionaries to CSV for analysis or use in other applications.
- **Read real names from a file and save names of length 5 to a CSV file**
  - Filter real names from a text file and save only those with exactly 5 characters to a CSV file.
- **Play a guessing game**
  - Generates 1000 random names (length 5)
  - Prompts the user for 6 names (length 5)
  - Computer selects 5 random names from the generated list
  - User has 3 attempts to guess any of the computer's selected names
  - Prints "win" if guessed correctly, otherwise "lose"

---

### Usage

#### 1. Generate and Save Word Frequencies

To generate a dictionary of random words and their frequencies, and save it to a CSV file:

```python
word_freqs = generate_word_frequencies()
save_word_frequencies_to_csv(word_freqs)
```
This will create `word_frequencies.csv` in your working directory.

#### 2. Generate and Save Random Words

To generate 1000 random words (length 5) and save them to a CSV file:

```python
random_word_freqs = generate_random_words_with_frequencies()
save_word_frequencies_to_csv(random_word_freqs, filename="random_words.csv")
```

#### 3. Save Real Names of Length 5 to CSV

Prepare a file named `names.txt` in your project directory, with one real name per line. Then run:

```python
save_real_names_to_csv()
```
This will create `real_names.csv` containing up to 1000 real names of length 5.

#### 4. Play the Guessing Game

To play the game, simply run:

```bash
python src/main.py
```
You will be prompted to enter 6 names (each exactly 5 characters). The computer will select 5 random names from its generated list. You have 3 attempts to guess any of the computer's selected names. If you guess correctly, you win; otherwise, you lose.

---

### Example Output

```
Enter name 1 (exactly 5 characters): apple
Enter name 2 (exactly 5 characters): berry
Enter name 3 (exactly 5 characters): mango
Enter name 4 (exactly 5 characters): peach
Enter name 5 (exactly 5 characters): lemon
Enter name 6 (exactly 5 characters): grape

Try to guess one of the computer's selected names!
Attempt 1: Enter your guess (exactly 5 characters): apple
Wrong guess.
Attempt 2: Enter your guess (exactly 5 characters): berry
Wrong guess.
Attempt 3: Enter your guess (exactly 5 characters): mango
win
```

---

### Requirements

No external dependencies required for basic functionality. All modules used are part of Python's standard library.
