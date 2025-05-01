class UnifiedNumerology:
	def __init__(self):
		self.alphabets = {}
		self.mappings = {}
		self.init_alphabets()
		self.generate_all_mappings()

	def init_alphabets(self):
		# Arabic - Abjadi Order (Traditional)
		self.alphabets['arabic_abjadi'] = [
			'ا', 'ب', 'ج', 'د', 'ه', 'و', 'ز', 'ح', 'ط', 'ي', 'ك', 'ل', 'م', 'ن',
			'س', 'ع', 'ف', 'ص', 'ق', 'ر', 'ش', 'ت', 'ث', 'خ', 'ذ', 'ض', 'ظ', 'غ'
		]

		# Arabic - Maghribi Abjadi Order (North African variant)
		self.alphabets['arabic_maghribi'] = [
			'ا', 'ب', 'ج', 'د', 'ه', 'و', 'ز', 'ح', 'ط', 'ي', 'ك', 'ل', 'م', 'ن',
			'ص', 'ع', 'ف', 'ض', 'ق', 'ر', 'س', 'ت', 'ث', 'خ', 'ذ', 'ظ', 'ش', 'غ'
		]

		# Arabic - Hija Order (Modern)
		self.alphabets['arabic_hija'] = [
			'ا', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'س', 'ش', 'ص',
			'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي'
		]

		# Arabic - Maghribi Hija Order
		self.alphabets['arabic_maghribi_hija'] = [
			'ا', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'س', 'ش', 'ص',
			'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي'
		]

		# Hebrew Alphabet
		self.alphabets['hebrew'] = [
			'א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט', 'י', 'כ', 'ל', 'מ', 'נ',
			'ס', 'ע', 'פ', 'צ', 'ק', 'ר', 'ש', 'ת', 'ך', 'ם', 'ן', 'ף', 'ץ'
		]

		# English Alphabet
		self.alphabets['english'] = [
			'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
			'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
		]

		# Latin Alphabet (Classical)
		self.alphabets['latin'] = [
			'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
			'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'X', 'Y', 'Z'
		]

		# Turkish Alphabet
		self.alphabets['turkish'] = [
			'A', 'B', 'C', 'Ç', 'D', 'E', 'F', 'G', 'Ğ', 'H', 'I', 'İ', 'J', 'K', 'L', 'M',
			'N', 'O', 'Ö', 'P', 'R', 'S', 'Ş', 'T', 'U', 'Ü', 'V', 'Y', 'Z'
		]

		# Ottoman Alphabet
		self.alphabets['ottoman'] = [
			'ا', 'ب', 'پ', 'ت', 'ث', 'ج', 'چ', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'ژ', 'س', 'ش',
			'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'گ', 'ل', 'م', 'ن', 'و', 'ه', 'ی'
		]

	def generate_all_mappings(self):
		for alphabet_name, alphabet in self.alphabets.items():
			self.mappings[alphabet_name] = {
				'normal': self.generate_normal_mapping(alphabet),
				'inverse': self.generate_inverse_mapping(alphabet),
				'base36': self.generate_base36_mapping(alphabet),
				'base36_inverse': self.generate_base36_inverse_mapping(alphabet),
				'base100': self.generate_base100_mapping(alphabet),
				'base100_inverse': self.generate_base100_inverse_mapping(alphabet)
			}

	def generate_normal_mapping(self, alphabet):
		mapping = {}
		for i, letter in enumerate(alphabet, 1):
			mapping[letter] = i
		mapping[' '] = 0
		return mapping

	def generate_inverse_mapping(self, alphabet):
		mapping = {}
		count = len(alphabet)
		for letter in alphabet:
			mapping[letter] = count
			count -= 1
		mapping[' '] = 0
		return mapping

	def generate_base36_mapping(self, alphabet):
		mapping = {}
		for i, letter in enumerate(alphabet, 36):
			mapping[letter] = i
		mapping[' '] = 0
		return mapping

	def generate_base36_inverse_mapping(self, alphabet):
		mapping = {}
		count = 36 + len(alphabet) - 1
		for letter in alphabet:
			mapping[letter] = count
			count -= 1
		mapping[' '] = 0
		return mapping

	def generate_base100_mapping(self, alphabet):
		mapping = {}
		for i, letter in enumerate(alphabet, 100):
			mapping[letter] = i
		mapping[' '] = 0
		return mapping

	def generate_base100_inverse_mapping(self, alphabet):
		mapping = {}
		count = 100 + len(alphabet) - 1
		for letter in alphabet:
			mapping[letter] = count
			count -= 1
		mapping[' '] = 0
		return mapping

	def numerolog(self, text, alphabet='turkish', method='normal', detail=False):
		alphabet_key = self.get_alphabet_key(alphabet)
		if alphabet_key not in self.mappings or method not in self.mappings[alphabet_key]:
			return {'error': 'Unsupported alphabet or method'}

		mapping = self.mappings[alphabet_key][method]
		return self.calculate_value(text, mapping, alphabet_key, detail)

	def get_alphabet_key(self, alphabet):
		alphabet = alphabet.lower()
		aliases = {
			'arabic': 'arabic_abjadi',
			'abjad': 'arabic_abjadi',
			'maghribi': 'arabic_maghribi',
			'hija': 'arabic_hija',
			'maghribi_hija': 'arabic_maghribi_hija',
			'osman': 'ottoman',
			'ottoman_turkish': 'ottoman'
		}
		return aliases.get(alphabet, alphabet)

	def calculate_value(self, text, mapping, alphabet, detail=False):
		result = 0
		detail_text = ''

		if alphabet in ['turkish', 'english', 'latin']:
			text = text.upper()

		for char in text:
			if char in mapping:
				value = mapping[char]
				if detail:
					detail_text += f"[{char}={value}]"
				else:
					result += value
			elif alphabet in ['turkish', 'english', 'latin']:
				upper_char = char.upper()
				if upper_char in mapping:
					value = mapping[upper_char]
					if detail:
						detail_text += f"[{char}={value}]"
					else:
						result += value

		return detail_text if detail else result

	def calculate_all(self, text, alphabet='turkish'):
		results = {}
		alphabet_key = self.get_alphabet_key(alphabet)

		results['normal'] = self.numerolog(text, alphabet_key, 'normal')
		results['inverse'] = self.numerolog(text, alphabet_key, 'inverse')
		results['base36'] = self.numerolog(text, alphabet_key, 'base36')
		results['base36_inverse'] = self.numerolog(text, alphabet_key, 'base36_inverse')
		results['base100'] = self.numerolog(text, alphabet_key, 'base100')
		results['base100_inverse'] = self.numerolog(text, alphabet_key, 'base100_inverse')

		results['base3'] = results['normal'] * 3
		results['base6'] = results['normal'] * 6
		results['base9'] = results['normal'] * 9
		results['base3_inverse'] = results['inverse'] * 3
		results['base6_inverse'] = results['inverse'] * 6
		results['base9_inverse'] = results['inverse'] * 9

		results['diff'] = {
			'normal': results['normal'] - results['inverse'],
			'base3': results['base3'] - results['base3_inverse'],
			'base6': results['base6'] - results['base6_inverse'],
			'base9': results['base9'] - results['base9_inverse'],
			'base36': results['base36'] - results['base36_inverse'],
			'base100': results['base100'] - results['base100_inverse']
		}

		return results

	def get_mapping(self, alphabet, method='normal'):
		alphabet_key = self.get_alphabet_key(alphabet)
		return self.mappings.get(alphabet_key, {}).get(method)

	def get_available_alphabets(self):
		return list(self.alphabets.keys())

	def get_available_methods(self):
		return ['normal', 'inverse', 'base36', 'base36_inverse', 'base100', 'base100_inverse']

	def get_alphabet(self, alphabet):
		alphabet_key = self.get_alphabet_key(alphabet)
		return self.alphabets.get(alphabet_key)