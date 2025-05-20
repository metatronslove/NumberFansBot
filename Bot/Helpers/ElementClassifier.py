import unicodedata

class ElementClassifier:
	# Element mappings for each guide and element type
	ELEMENT_MAPPINGS = {
		'TURKCE': {
			'fire': ['A', 'D', 'Ğ', 'J', 'N', 'R', 'U', 'Z'],
			'air': ['B', 'E', 'H', 'K', 'O', 'S', 'Ü'],
			'water': ['C', 'F', 'I', 'L', 'Ö', 'Ş', 'V'],
			'earth': ['Ç', 'G', 'İ', 'M', 'P', 'T', 'Y']
		},
		'HEBREW': {
			'fire': ['א', 'ה', 'ט', 'מ', 'פ', 'ש', 'ף'],
			'air': ['ב', 'ו', 'י', 'נ', 'צ', 'ת', 'ץ'],
			'water': ['ג', 'ז', 'כ', 'ס', 'ק', 'ם', 'ך'],
			'earth': ['ד', 'ח', 'ל', 'ע', 'ר', 'ן']
		},
		'ARABI': {
			'fire': ['ا', 'ه', 'ط', 'م', 'ف', 'ش', 'ذ'],
			'air': ['د', 'ح', 'ل', 'ع', 'ر', 'خ', 'غ'],
			'water': ['ب', 'و', 'ن', 'ي', 'ی', 'ص', 'ت', 'ض'],
			'earth': ['ج', 'ز', 'ك', 'س', 'ق', 'ث', 'ظ']
		},
		'BUNI': {
			'fire': ['ا', 'ه', 'ط', 'م', 'ف', 'ش', 'ذ'],
			'air': ['ب', 'و', 'ن', 'ي', 'ی', 'ص', 'ت', 'ض'],
			'water': ['د', 'ح', 'ل', 'ع', 'ر', 'خ', 'غ'],
			'earth': ['ج', 'ز', 'ك', 'س', 'ق', 'ث', 'ظ']
		},
		'HUSEYNI': {
			'fire': ['ا', 'ه', 'ط', 'م', 'ف', 'ش', 'ذ'],
			'air': ['ج', 'ز', 'ك', 'س', 'ق', 'ث', 'ظ'],
			'water': ['د', 'ح', 'ل', 'ع', 'ر', 'خ', 'غ'],
			'earth': ['ب', 'و', 'ي', 'ی', 'ن', 'ص', 'ت', 'ض']
		},
		'ENGLISH': {
			'fire': ['A', 'E', 'I', 'M', 'Q', 'U', 'Y'],
			'air': ['B', 'F', 'J', 'N', 'R', 'V', 'Z'],
			'water': ['C', 'G', 'K', 'O', 'S', 'W'],
			'earth': ['D', 'H', 'L', 'P', 'T', 'X']
		},
		'LATIN': {
			'fire': ['A', 'E', 'I', 'M', 'Q', 'U', 'Y'],
			'air': ['B', 'F', 'J', 'N', 'R', 'V', 'Z'],
			'water': ['C', 'G', 'K', 'O', 'S', 'W'],
			'earth': ['D', 'H', 'L', 'P', 'T', 'X']
		},
		'DEFAULT': {
			'fire': ['ا', 'ب', 'ج', 'س', 'ص', 'ر', 'خ'],
			'air': ['ه', 'ز', 'ح', 'ط', 'ي', 'ل', 'ة', 'ث', 'ی'],
			'water': ['د', 'ك', 'ع', 'ف', 'ق', 'ش', 'ض'],
			'earth': ['و', 'م', 'ن', 'ت', 'ذ', 'ظ', 'غ']
		}
	}

	def __init__(self):
		self.shadda_char = '\u0651'	# Arabic shadda (U+0651)
		self.valid_guides = ['TURKCE', 'ARABI', 'BUNI', 'HUSEYNI', 'HEBREW', 'ENGLISH', 'LATIN']
		self.valid_elements = ['fire', 'air', 'water', 'earth']

	def _normalize_char(self, char: str, guide: str) -> str:
		"""Normalize special characters based on guide."""
		arabic_chars = ['ا', 'ب', 'ج', 'س', 'ص', 'ر', 'خ', 'ه', 'ز', 'ح', 'ط', 'ي', 'ی', 'ل', 'ة', 'ث', 'د', 'ك', 'ع', 'ف', 'ق', 'ش', 'ض', 'و', 'م', 'ن', 'ت', 'ذ', 'ظ', 'غ']
		hebrew_chars = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט', 'י', 'כ', 'ל', 'מ', 'נ', 'ס', 'ע', 'פ', 'צ', 'ק', 'ר', 'ש', 'ת', 'ם', 'ן', 'ף', 'ץ', 'ך']
		latin_chars = ['A', 'B', 'C', 'Ç', 'D', 'E', 'F', 'G', 'Ğ', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'Ö', 'P', 'R', 'S', 'Ş', 'T', 'U', 'Ü', 'V', 'Y', 'Z', 'Q', 'W', 'X']

		if char in arabic_chars:
			return char
		elif char in ['أ', 'إ', 'آ', 'ء', 'ى']:
			return 'ا'
		elif char == 'ؤ':
			return 'و' + 'ا'
		elif char == 'ۀ':
			return 'ه' + 'ي'
		elif char == 'ئ':
			return 'ي' + 'ا'
		elif char in hebrew_chars:
			return char
		elif char.upper() in latin_chars:
			return char.upper()
		elif char in ['İ', 'i']:
			return 'İ' if guide in ['TURKCE', '0'] else 'I'
		elif char in ['I', 'ı']:
			return 'I' if guide in ['TURKCE', '0', 'ENGLISH', 'LATIN', '5'] else 'I'
		return char

	def _mb_str_split(self, text: str) -> list:
		"""Split UTF-8 string into individual characters."""
		return [char for char in unicodedata.normalize('NFC', text)]

	def classify_elements(self, text: str, element_type: str, shadda: int = 1, guide: str = '0') -> dict:
		"""
		Classify letters in text into elements (fire, air, water, earth) based on guide and element type.

		Args:
			text (str): Input text to process.
			output_type (str/int): 'list'/'liste'/1 for list of letters, 'amount'/'adet'/0 for count.
			element_type (str/int): 'fire'/'ateş'/0, 'air'/'hava'/1, 'water'/'su'/2, 'earth'/'toprak'/3.
			shadda (int): 1 (ignore shadda), 2 (double previous letter).
			guide (str/int): Language/method ('TURKCE'/0, 'ARABI'/1, 'BUNI'/2, 'HUSEYNI'/3, 'HEBREW'/4, 'ENGLISH', 'LATIN', or default).

		Returns:
			str: List of matching letters, count, or 'Hata?' on error.
		"""
		try:
			# Normalize inputs
			guide = str(guide).upper() if isinstance(guide, (str, int)) else 'DEFAULT'
			guide = {
				'0': 'TURKCE',
				'1': 'ARABI',
				'2': 'BUNI',
				'3': 'HUSEYNI',
				'4': 'HEBREW',
				'5': 'ENGLISH'
			}.get(guide, guide)
			if guide not in self.valid_guides:
				guide = 'DEFAULT'

			element_type = str(element_type).lower()
			element_type = {
				'ateş': 'fire',
				'hava': 'air',
				'su': 'water',
				'toprak': 'earth',
				'0': 'fire',
				'1': 'air',
				'2': 'water',
				'3': 'earth',
				'fire': 'fire',
				'air': 'air',
				'water': 'water',
				'earth': 'earth'
			}.get(element_type, element_type)
			if element_type not in self.valid_elements:
				return 'Hata?'

			shadda = int(shadda)
			if shadda not in [1, 2]:
				return 'Hata?'

			# Split text into characters
			chars = self._mb_str_split(text)
			selected = ''
			t = 0

			# Filter and normalize characters
			for selectable in chars:
				if selectable == self.shadda_char and shadda == 2:
					c = 1
					while t - c >= 0 and not chars[t - c].strip():
						c += 1
					if t - c >= 0:
						selectable = chars[t - c]
				selected += self._normalize_char(selectable, guide)
				t += 1

			# Classify elements
			liste = ''
			adet = 0
			for char in self._mb_str_split(selected):
				if char in self.ELEMENT_MAPPINGS[guide][element_type]:
					liste += char + ' '
					adet += 1
			return {"adet": adet, "liste": liste.strip()}
		except Exception:
			return 'Hata?'