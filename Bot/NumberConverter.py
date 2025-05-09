class NumberConverter:
	def indian(self, metin):
		number_map = {
			'0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤',
			'5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩', ' ': ' '
		}
		return ''.join(number_map.get(char, char) for char in metin)

	def arabic(self, metin):
		number_map = {
			'٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
			'٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9', ' ': ' '
		}
		return ''.join(number_map.get(char, char) for char in metin)

	def arab_to_indian(self, value):
		return self.indian(str(value))