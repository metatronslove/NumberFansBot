import re
import math
import random
from typing import Union, List, Dict, Tuple, Optional

class Abjad:
	def __init__(self):
		self.mappings = {
			"arabic": {
				1: {
					"ا": 1, "ب": 2, "ج": 3, "د": 4, "ه": 5, "و": 6, "ز": 7, "ح": 8, "ط": 9,
					"ي": 10, "ك": 20, "ل": 30, "م": 40, "ن": 50, "س": 60, "ع": 70, "ف": 80,
					"ص": 90, "ق": 100, "ر": 200, "ش": 300, "ت": 400, "ث": 500, "خ": 600,
					"ذ": 700, "ض": 800, "ظ": 900, "غ": 1000
				},
				7: {
					"ا": 1, "ب": 2, "ج": 3, "د": 4, "ه": 5, "و": 6, "ز": 7, "ح": 8, "ط": 9,
					"ي": 10, "ك": 20, "ل": 30, "م": 40, "ن": 50, "س": 300, "ع": 70, "ف": 80,
					"ص": 60, "ق": 100, "ر": 200, "ش": 1000, "ت": 400, "ث": 500, "خ": 600,
					"ذ": 700, "ض": 90, "ظ": 800, "غ": 900
				},
				12: {
					"ا": 1, "ب": 9, "ج": 100, "د": 70, "ه": 7, "و": 5, "ز": 600, "ح": 90, "ط": 800,
					"ي": 6, "ك": 20, "ل": 2, "م": 4, "ن": 3, "س": 60, "ع": 30, "ف": 40, "ص": 400,
					"ق": 50, "ر": 8, "ش": 300, "ت": 10, "ث": 700, "خ": 200, "ذ": 80, "ض": 500,
					"ظ": 1000, "غ": 900
				},
				17: {
					"ا": 1, "ب": 2, "ج": 5, "د": 8, "ه": 800, "و": 900, "ز": 20, "ح": 6, "ط": 70,
					"ي": 1000, "ك": 400, "ل": 500, "م": 600, "ن": 700, "س": 30, "ع": 90, "ف": 200,
					"ص": 50, "ق": 300, "ر": 10, "ش": 40, "ت": 3, "ث": 4, "خ": 7, "ذ": 9, "ض": 60,
					"ظ": 80, "غ": 100
				},
				22: {
					"ا": 1, "ب": 2, "ج": 3, "د": 4, "ه": 800, "و": 900, "ز": 20, "ح": 6, "ط": 30,
					"ي": 1000, "ك": 50, "ل": 60, "م": 70, "ن": 80, "س": 600, "ع": 200, "ف": 400,
					"ص": 100, "ق": 500, "ر": 10, "ش": 700, "ت": 3, "ث": 4, "خ": 7, "ذ": 9, "ض": 100,
					"ظ": 40, "غ": 300
				},
				27: {
					"ا": 1, "ب": 2, "ج": 5, "د": 8, "ه": 700, "و": 40, "ز": 600, "ح": 6, "ط": 100,
					"ي": 1000, "ك": 10, "ل": 20, "م": 30, "ن": 50, "س": 800, "ع": 80, "ف": 300,
					"ص": 60, "ق": 400, "ر": 500, "ش": 900, "ت": 3, "ث": 4, "خ": 7, "ذ": 9, "ض": 70,
					"ظ": 200, "غ": 90
				},
				32: {
					"ا": 1, "ب": 2, "ج": 5, "د": 8, "ه": 900, "و": 800, "ز": 20, "ح": 6, "ط": 70,
					"ي": 1000, "ك": 400, "ل": 500, "م": 600, "ن": 700, "س": 30, "ع": 90, "ف": 200,
					"ص": 50, "ق": 300, "ر": 10, "ش": 40, "ت": 3, "ث": 4, "خ": 7, "ذ": 9, "ض": 60,
					"ظ": 80, "غ": 100
				}
			},
			"hebrew": {
				1: {
					"א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9,
					"י": 10, "כ": 20, "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80,
					"צ": 90, "ק": 100, "ר": 200, "ש": 300, "ת": 400, "ך": 500, "ם": 600,
					"ן": 700, "ף": 800, "ץ": 900
				}
			},
			"turkish": {
				1: {
					"a": 1, "b": 2, "c": 3, "ç": 3, "d": 4, "e": 5, "f": 6, "g": 7, "ğ": 8,
					"h": 9, "ı": 10, "i": 20, "j": 30, "k": 40, "l": 50, "m": 60, "n": 70,
					"o": 80, "ö": 90, "p": 100, "r": 200, "s": 300, "ş": 400, "t": 500, "u": 600,
					"ü": 700, "v": 800, "y": 900, "z": 1000
				}
			},
			"english": {
				1: {
					"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8, "i": 9,
					"j": 10, "k": 20, "l": 30, "m": 40, "n": 50, "o": 60, "p": 70, "q": 80,
					"r": 90, "s": 100, "t": 200, "u": 300, "v": 400, "w": 500, "x": 600,
					"y": 700, "z": 800
				}
			},
			"latin": {
				1: {
					"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8, "i": 9,
					"j": 10, "k": 20, "l": 30, "m": 40, "n": 50, "o": 60, "p": 70, "q": 80,
					"r": 90, "s": 100, "t": 200, "u": 300, "v": 400, "w": 500, "x": 600,
					"y": 700, "z": 800
				}
			}
		}

		self.special_letters = {
			"arabic": {
				"ء": ["ا"], "أ": ["ا"], "إ": ["ا"], "آ": ["ا"], "ؤ": ["و", "ا"], "ئ": ["ي", "ا"],
				"ﯓ": ["ن"], "ک": ["ك"], "ﮒ": ["ك"], "ﮊ": ["ز"], "ﭺ": ["ج"], "ﭖ": ["ب"], "ة": ["ه"]
			},
			"hebrew": {},
			"turkish": {},
			"english": {},
			"latin": {}
		}

		self.letter_pronunciations = {
			"arabic": {
				"ا": "الف", "ب": "با", "ج": "جيم", "د": "دال", "ه": "ها", "و": "واو", "ز": "زا",
				"ح": "حا", "ط": "طا", "ي": "يا", "ك": "كاف", "ل": "لام", "م": "ميم", "ن": "نون",
				"س": "سين", "ع": "عين", "ف": "فا", "ص": "صاد", "ق": "قاف", "ر": "را", "ش": "شين",
				"ت": "تا", "ث": "ثا", "خ": "خا", "ذ": "ذال", "ض": "ضاد", "ظ": "ظا", "غ": "غين",
				"ء": "همزة", "أ": "ألف", "إ": "ألف", "آ": "ألف", "ؤ": "واو", "ئ": "يا"
			},
			"hebrew": {
				"א": "אלף", "ב": "בית", "ג": "גימל", "ד": "דלת", "ה": "הא", "ו": "וואו", "ז": "זין",
				"ח": "חית", "ט": "טית", "י": "יוד", "כ": "כף", "ל": "למד", "מ": "מם", "נ": "נון",
				"ס": "סמך", "ע": "עין", "פ": "פא", "צ": "צדי", "ק": "קוף", "ר": "ריש", "ש": "שין",
				"ת": "תו", "ך": "כף סופית", "ם": "מם סופית", "ן": "נון סופית", "ף": "פא סופית",
				"ץ": "צדי סופית"
			},
			"turkish": {
				"a": "a", "b": "be", "c": "ce", "ç": "çe", "d": "de", "e": "e", "f": "fe", "g": "ge",
				"ğ": "yumuşak ge", "j": "je", "k": "ka", "l": "le", "m": "me", "n": "ne", "o": "o",
				"ö": "ö", "p": "pe", "r": "re", "s": "se", "t": "te", "u": "u", "ü": "ü", "v": "ve",
				"y": "ye", "z": "ze", "ş": "şe", "ı": "ı"
			},
			"english": {
				"a": "ay", "b": "bee", "c": "see", "d": "dee", "e": "ee", "f": "eff", "g": "gee",
				"h": "aitch", "i": "eye", "j": "jay", "k": "kay", "l": "ell", "m": "em", "n": "en",
				"o": "oh", "p": "pee", "q": "cue", "r": "ar", "s": "ess", "t": "tee", "u": "you",
				"v": "vee", "w": "double you", "x": "ex", "y": "why", "z": "zee"
			},
			"latin": {
				"a": "a", "b": "be", "c": "ce", "d": "de", "e": "e", "f": "ef", "g": "ge", "h": "ha",
				"i": "i", "j": "ji", "k": "ka", "l": "el", "m": "em", "n": "en", "o": "o", "p": "pe",
				"q": "qu", "r": "er", "s": "es", "t": "te", "u": "u", "v": "ve", "w": "double u",
				"x": "ix", "y": "y", "z": "zed"
			}
		}

	def abjad(self, metin: str, tablo: int = 1, shadda: int = 1, detail: int = 0, lang: str = "arabic") -> Union[int, Dict[str, Union[int, List[Dict[str, Union[str, int]]]]]]:
		base_table = tablo
		calculation_method = "Small Abjad"
		effective_table = tablo

		# Determine calculation method
		base_tables = list(self.mappings[lang].keys())
		for bt in base_tables:
			if tablo == bt - 1:
				calculation_method = "Minimum Abjad"
				base_table = bt
				effective_table = bt - 1
				break
			elif tablo == bt + 1:
				calculation_method = "Big Abjad"
				base_table = bt
				effective_table = bt + 1
				break
			elif tablo == bt + 2:
				calculation_method = "Biggest Abjad"
				base_table = bt
				effective_table = bt + 2
				break

		# Validate effective table
		if effective_table not in self.mappings[lang]:
			effective_table = base_table

		# Split string into characters
		chars = list(metin.encode('utf-8').decode('utf-8'))
		sum_value = 0
		details = []
		shadda_char = "ّ"

		i = 0
		while i < len(chars):
			char = chars[i].lower()
			value = 0

			# Handle special letters
			if char in self.special_letters[lang]:
				for component in self.special_letters[lang][char]:
					if calculation_method == "Big Abjad":
						pronunciation = self.letter_pronunciations[lang].get(component, component)
						component_value = self.abjad(pronunciation, base_table, shadda, 0, lang)
					else:
						component_value = self.abjad(component, base_table, shadda, 0, lang)

					if calculation_method == "Minimum Abjad":
						component_value = self.asgar(component_value)
					elif calculation_method == "Biggest Abjad":
						component_value = self.bastet(str(component_value), 1, -effective_table - 1, shadda, lang)

					value += component_value
			else:
				if calculation_method == "Big Abjad":
					pronunciation = self.letter_pronunciations[lang].get(char, char)
					value = self.abjad(pronunciation, base_table, shadda, 0, lang)
				else:
					value = self.mappings[lang].get(effective_table, {}).get(char, 0)

					if calculation_method == "Minimum Abjad":
						value = self.asgar(value)
					elif calculation_method == "Biggest Abjad":
						value = self.bastet(str(value), 1, effective_table, shadda, lang)

			# Handle shadda
			if shadda and lang == "arabic" and i + 1 < len(chars) and chars[i + 1] == shadda_char:
				value *= 2
				i += 1

			sum_value += value
			if detail == 1:
				details.append({"char": char, "value": value})

			i += 1

		return {"sum": sum_value, "details": details} if detail == 1 else sum_value

	def bastet(self, metin: int, mt: int, tablo: int = 1, shadda: int = 1, language: str = "ARABIC", detail: int = 0) -> str:
		try:
			err = 0
			language = language.upper()

			if metin:
				baster = int(metin)
			else:
				if 0 <= tablo <= 15:
					baster = self.abjad(metin, tablo, shadda, 0, language.lower())
				elif -16 <= tablo < 0:
					invertablo = -tablo - 1
					baster = self.abjad(metin, invertablo, shadda, 0, language.lower())

			for _ in range(mt):
				ns = self.nutket(baster, language)
				baster = 0

				if 0 <= tablo <= 15:
					baster = self.abjad(ns, tablo, 1, 0, language.lower()) + self.abjad(ns, 5, 1, 0, language.lower())
				elif -16 <= tablo < 0:
					baster = self.abjad(ns, invertablo, 1, 0, language.lower())
				else:
					baster = "Tablo Kodu?"
					err = 1

			if err == 0:
				return ns if detail == 1 else baster
			elif err == 1:
				return "Dil?"
		except Exception as e:
			return f"Error: {str(e)}"

	def asgar(self, input_value: int) -> int:
		return input_value % 12

	def saf(self, metin: str, ayrac: Union[str, int] = " ", shadda: int = 1, lang: str = "arabic") -> str:
		try:
			result = ""
			irun = "" if ayrac == 0 else ayrac
			chars = list(metin.encode('utf-8').decode('utf-8'))
			shadda_char = "ّ"
			i = 0

			while i < len(chars):
				char = chars[i]
				s = ""

				if char == " ":
					s = " " if ayrac == "" else irun
				elif lang == "arabic" and char == shadda_char and i > 0 and shadda:
					if chars[i - 1] in self.mappings[lang][1] or chars[i - 1] in self.special_letters[lang]:
						result += chars[i - 1] + irun
					i += 1
					continue
				elif char in self.mappings[lang][1] or char in self.special_letters[lang]:
					s = char + irun
				elif char in ["İ", "i"]:
					if lang in ["turkish", "english", "latin"]:
						s = "i"
				elif char in ["I", "ı"]:
					if lang == "turkish":
						s = "ı"
					elif lang in ["english", "latin"]:
						s = "i"
				else:
					s = ""

				result += s
				i += 1

			return result.rstrip(irun) if irun else result
		except Exception as e:
			return f"Error: {str(e)}"

	def nutket(self, mynumber: Union[int, str], language: str = "ARABIC", gender: str = "female") -> str:
		try:
			language = language.upper()
			gender = gender.lower()
			if isinstance(mynumber, str):
				if not mynumber.isdigit():
					return "Geçersiz sayı formatı"
				mynumber = int(mynumber)
			if mynumber == 0:
				return self.ZERO_MAP.get(language, {}).get(gender, "zero")
			return self.convert_large_number(mynumber, language, gender)
		except Exception as e:
			return f"Hata: {str(e)}"

	def convert_large_number(self, num: int, lang: str, gender: str) -> str:
		parts = []
		scale_index = 0
		scales = self.SCALE_MAP.get(lang, [])
		while num > 0:
			chunk = num % 1000
			num = num // 1000
			if chunk != 0:
				part = self.convert_chunk(chunk, lang, gender)
				if scale_index > 0 and scale_index < len(scales):
					part += " " + self.get_scale_word(chunk, lang, scale_index)
				parts.insert(0, part)
			scale_index += 1
		return self.join_parts(parts, lang)

	def convert_chunk(self, num: int, lang: str, gender: str) -> str:
		if num >= 100:
			return self.convert_hundreds(num, lang, gender)
		elif num >= 20:
			return self.convert_tens(num, lang, gender)
		else:
			return self.convert_small(num, lang, gender)

	def convert_hundreds(self, num: int, lang: str, gender: str) -> str:
		hundreds_digit = num // 100
		remainder = num % 100
		result = []
		if hundreds_digit > 0:
			if lang == "ARABIC":
				result.append(self.ARABIC_HUNDREDS[hundreds_digit])
			elif lang == "TURKISH":
				prefix = self.TURKISH_NUMBERS[hundreds_digit] + " " if hundreds_digit > 1 else ""
				result.append(f"{prefix}yüz")
			elif lang == "ENGLISH":
				result.append(self.ENGLISH_BELOW_20[hundreds_digit] + " hundred")
			elif lang == "LATIN":
				result.append(self.LATIN_HUNDREDS[hundreds_digit])
			elif lang == "HEBREW":
				result.append(self.HEBREW_HUNDREDS[hundreds_digit])
		if remainder > 0:
			result.append(self.convert_tens(remainder, lang, gender))
		return " ".join(result).strip()

	def convert_tens(self, num: int, lang: str, gender: str) -> str:
		if lang == "TURKISH":
			tens = (num // 10) * 10
			ones = num % 10
			return f"{self.TURKISH_NUMBERS[tens]} {self.TURKISH_NUMBERS[ones]}".strip()
		elif lang == "ENGLISH":
			if num < 20:
				return self.ENGLISH_BELOW_20[num]
			tens = num // 10
			ones = num % 10
			return f"{self.ENGLISH_TENS[tens]}-{self.ENGLISH_BELOW_20[ones]}" if ones > 0 else self.ENGLISH_TENS[tens]
		elif lang == "LATIN":
			tens = num // 10
			ones = num % 10
			latin = self.LATIN_TENS.get(tens * 10, "")
			return f"{latin} {self.LATIN_UNITS.get(ones, '')}".strip()
		elif lang == "ARABIC":
			return self.convert_small(num, lang, gender)
		elif lang == "HEBREW":
			return self.convert_small(num, lang, gender)
		return str(num)

	def convert_small(self, num: int, lang: str, gender: str) -> str:
		if lang == "TURKISH":
			return self.TURKISH_NUMBERS.get(num, "")
		elif lang == "ENGLISH":
			return self.ENGLISH_BELOW_20[num]
		elif lang == "LATIN":
			return self.LATIN_UNITS.get(num, "")
		elif lang == "ARABIC":
			return self.ARABIC_NUMBERS[gender].get(num, "")
		elif lang == "HEBREW":
			return self.HEBREW_NUMBERS[gender].get(num, "")
		return str(num)

	def get_scale_word(self, chunk: int, lang: str, index: int) -> str:
		word = self.SCALE_MAP.get(lang, [""])[index]
		if lang == "TURKISH" and chunk == 1 and index == 1:
			return "bin"  # Türkçede 'bir bin' denmez
		return word

	def join_parts(self, parts: List[str], lang: str) -> str:
		if lang == "ARABIC":
			return " و ".join(parts)
		elif lang == "TURKISH":
			return " ".join(parts)
		elif lang == "ENGLISH":
			return ", ".join(parts)
		elif lang == "HEBREW":
			return " ו ".join(parts)
		elif lang == "LATIN":
			return " et ".join(parts)
		return " ".join(parts)

	# Veri Haritaları:
	ZERO_MAP = {
		"ARABIC": {"male": "صفر", "female": "صفر"},
		"HEBREW": {"male": "אפס", "female": "אפס"},
		"LATIN": {"male": "nulla", "female": "nulla"},
		"ENGLISH": {"male": "zero", "female": "zero"},
		"TURKISH": {"male": "sıfır", "female": "sıfır"}
	}

	SCALE_MAP = {
		"TURKISH": ["", "bin", "milyon", "milyar", "trilyon"],
		"ENGLISH": ["", "thousand", "million", "billion", "trillion"],
		"HEBREW": ["", "אלף", "מיליון", "מיליארד", "טריליון"],
		"LATIN": ["", "milia", "milionem", "miliardum", "trilio"],
		"ARABIC": ["", "ألف", "مليون", "مليار", "تريليون"]
	}

	TURKISH_NUMBERS = {
		0: "", 1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş",
		6: "altı", 7: "yedi", 8: "sekiz", 9: "dokuz",
		10: "on", 20: "yirmi", 30: "otuz", 40: "kırk",
		50: "elli", 60: "altmış", 70: "yetmiş",
		80: "seksen", 90: "doksan"
	}

	ENGLISH_BELOW_20 = ["", "one", "two", "three", "four", "five", "six",
						"seven", "eight", "nine", "ten", "eleven", "twelve",
						"thirteen", "fourteen", "fifteen", "sixteen",
						"seventeen", "eighteen", "nineteen"]

	ENGLISH_TENS = ["", "ten", "twenty", "thirty", "forty", "fifty",
					"sixty", "seventy", "eighty", "ninety"]

	ARABIC_NUMBERS = {
		"male": {
			1: "واحد", 2: "اثنان", 3: "ثلاثة", 4: "أربعة",
			5: "خمسة", 6: "ستة", 7: "سبعة", 8: "ثمانية",
			9: "تسعة", 10: "عشرة", 11: "أحد عشر", 12: "اثنا عشر",
			13: "ثلاثة عشر", 14: "أربعة عشر", 15: "خمسة عشر",
			16: "ستة عشر", 17: "سبعة عشر", 18: "ثمانية عشر", 19: "تسعة عشر",
			20: "عشرون", 30: "ثلاثون", 40: "أربعون", 50: "خمسون",
			60: "ستون", 70: "سبعون", 80: "ثمانون", 90: "تسعون"
		},
		"female": {
			1: "واحدة", 2: "اثنتان", 3: "ثلاث", 4: "أربع",
			5: "خمس", 6: "ست", 7: "سبع", 8: "ثمان",
			9: "تسع", 10: "عشر", 11: "إحدى عشرة", 12: "اثنتا عشرة",
			13: "ثلاث عشرة", 14: "أربع عشرة", 15: "خمس عشرة",
			16: "ست عشرة", 17: "سبع عشرة", 18: "ثماني عشرة", 19: "تسع عشرة",
			20: "عشرون", 30: "ثلاثون", 40: "أربعون", 50: "خمسون",
			60: "ستون", 70: "سبعون", 80: "ثمانون", 90: "تسعون"
		}
	}

	ARABIC_HUNDREDS = {
		1: "مائة", 2: "مائتان", 3: "ثلاثمائة", 4: "أربعمائة",
		5: "خمسمائة", 6: "ستمائة", 7: "سبعمائة", 8: "ثمانمائة", 9: "تسعمائة"
	}

	LATIN_UNITS = {
		0: "", 1: "unus", 2: "duo", 3: "tres", 4: "quattuor",
		5: "quinque", 6: "sex", 7: "septem", 8: "octo", 9: "novem",
		10: "decem", 11: "undecim", 12: "duodecim", 13: "tredecim",
		14: "quattuordecim", 15: "quindecim", 16: "sedecim",
		17: "septendecim", 18: "duodeviginti", 19: "undeviginti"
	}

	LATIN_TENS = {
		20: "viginti", 30: "triginta", 40: "quadraginta",
		50: "quinquaginta", 60: "sexaginta", 70: "septuaginta",
		80: "octoginta", 90: "nonaginta"
	}

	LATIN_HUNDREDS = {
		1: "centum", 2: "ducenti", 3: "trecenti", 4: "quadringenti",
		5: "quingenti", 6: "sescenti", 7: "septingenti", 8: "octingenti", 9: "nongenti"
	}

	HEBREW_NUMBERS = {
		"male": {
			1: "אחד", 2: "שניים", 3: "שלושה", 4: "ארבעה",
			5: "חמישה", 6: "שישה", 7: "שבעה", 8: "שמונה",
			9: "תשעה", 10: "עשרה", 20: "עשרים", 30: "שלושים",
			40: "ארבעים", 50: "חמישים", 60: "שישים", 70: "שבעים",
			80: "שמונים", 90: "תשעים"
		},
		"female": {
			1: "אחת", 2: "שתיים", 3: "שלוש", 4: "ארבע",
			5: "חמש", 6: "שש", 7: "שבע", 8: "שמונה",
			9: "תשע", 10: "עשר", 20: "עשרים", 30: "שלושים",
			40: "ארבעים", 50: "חמישים", 60: "שישים", 70: "שבעים",
			80: "שמונים", 90: "תשעים"
		}
	}

	HEBREW_HUNDREDS = {
		1: "מאה", 2: "מאתיים", 3: "שלוש מאות", 4: "ארבע מאות",
		5: "חמש מאות", 6: "שש מאות", 7: "שבע מאות",
		8: "שמונה מאות", 9: "תשע מאות"
	}

    def generate_arabic_name(self, hpart: Dict[int, str], counts: int, method: int, mode: str) -> str:
        """
        Arabic name generation supports two modes:
        - 'regular': positional (abjad) mapping
        - 'sum': sum-based spelling
        """
        # build raw numeric string
        raw = ''.join(hpart[i] for i in range(counts, 0, -1))
        if mode == 'regular':
            # positional mapping
            mapping = self.mappings['arabic'].get(method, self.mappings['arabic'][1])
            reverse_map = {v: k for k, v in mapping.items()}
            gh = ''
            for grp in range(counts, 0, -1):
                part = str(hpart[grp])
                for idx, ch in enumerate(part):
                    d = int(ch)
                    if d == 0:
                        continue
                    power = len(part) - idx - 1
                    value = d * (10 ** power)
                    gh += reverse_map.get(value, '')
            gh += getattr(self, '_current_suffix', '')
            return gh
        # eacher mode:
        # her grup sonrası eacher harfleri ekle
        mapping = self.mappings['arabic'].get(method, self.mappings['arabic'][1])
        reverse_map = {v: k for k, v in mapping.items()}
        gh = ''
        for counter in range(counts, 0, -1):
            part = str(hpart[counter])
            for idx, ch in enumerate(part):
                d = int(ch)
                if d == 0:
                    continue
                power = len(part) - idx - 1
                value = d * (10 ** power)
                gh += reverse_map.get(value, '')
            # eacher ekle
            gh += self._current_suffix
        return gh(raw, 'arabic')
        # else regular positional
        mapping = self.mappings['arabic'].get(method, self.mappings['arabic'][1])
        reverse_map = {v: k for k, v in mapping.items()}
        gh = ''
        for grp in range(counts, 0, -1):
            part = str(hpart[grp])
            for idx, ch in enumerate(part):
                d = int(ch)
                if d == 0:
                    continue
                power = len(part) - idx - 1
                value = d * (10 ** power)
                gh += reverse_map.get(value, '')
        gh += getattr(self, '_current_suffix', '')
        return gh

    def generate_hebrew_name(self, hpart: Dict[int, str], counts: int) -> str:
        raw = self._generate_generic(hpart, counts, self._current_method, 'hebrew')
        if self._current_mode == 'position':
            return self._apply_hebrew_grammar(self._position_spell(raw, 'hebrew'))
        # default 'sum' or other: sum-based spelling then grammar
        spelled = self._spell_by_sum(raw, 'hebrew')
        return self._apply_hebrew_grammar(spelled)

    def generate_english_name(self, hpart: Dict[int, str], counts: int) -> str:
        raw = self._generate_generic(hpart, counts, self._current_method, 'english')
        if self._current_mode == 'position':
            return self._apply_english_grammar(self._position_spell(raw, 'english'))
        spelled = self._spell_by_sum(raw, 'english')
        return self._apply_english_grammar(spelled)

    def generate_latin_name(self, hpart: Dict[int, str], counts: int) -> str:
        raw = self._generate_generic(hpart, counts, self._current_method, 'latin')
        if self._current_mode == 'position':
            return self._apply_latin_grammar(self._position_spell(raw, 'latin'))
        spelled = self._spell_by_sum(raw, 'latin')
        return self._apply_latin_grammar(spelled)

    def generate_turkish_name(self, hpart: Dict[int, str], counts: int) -> str:
        raw = self._generate_generic(hpart, counts, self._current_method, 'turkish')
        if self._current_mode == 'position':
            return self._apply_turkish_grammar(self._position_spell(raw, 'turkish'))
        spelled = self._spell_by_sum(raw, 'turkish')
        return self._apply_turkish_grammar(spelled)

    def _generate_generic(self, hpart: Dict[int, str], counts: int, method: int, language: str) -> str:
        # Her basamağın pozisyon değerlerini toplar
        target = sum(int(digit) * (10 ** (len(hpart[idx]) - pos - 1))
                     for idx in hpart
                     for pos, digit in enumerate(hpart[idx]))
        return str(target)

    def _position_spell(self, raw: str, language: str) -> str:
        # Harfleri pozisyon bazlı mapping ile doğrudan eşle
        mapping = self.mappings[language].get(self._current_method, self.mappings[language][1])
        reverse_map = {v: k for k, v in mapping.items()}
        res = ''
        for ch in raw:
            d = int(ch)
            if d == 0:
                continue
            # assume single-digit mapping
            res += reverse_map.get(d, '')
        res += getattr(self, '_current_suffix', '')
        return res

    def _spell_by_sum(self, raw: str, language: str) -> str:
        # raw: sayısal string, hedef sayı
        target = int(raw)
        mapping = self.mappings[language][1]
        items = sorted(mapping.items(), key=lambda kv: -kv[1])
        result = []
        rem = target
        for letter, val in items:
            while val <= rem:
                result.append(letter)
                rem -= val
        if rem > 0:
            closest = min(items, key=lambda kv: abs(kv[1] - rem))[0]
            result.append(closest)
        result.append(getattr(self, '_current_suffix', ''))
        return ''.join(result)

    # Dil bazlı gramer düzeltme:
    def _apply_english_grammar(self, s: str) -> str:
        vowels = 'aeiou'
        res = ''
        consec = 0
        for ch in s:
            res += ch
            if ch.lower() not in vowels:
                consec += 1
                if consec > 1:
                    res += random.choice(list(vowels))
                    consec = 0
            else:
                consec = 0
        return res

    def _apply_turkish_grammar(self, s: str) -> str:
        front = set('eiöü')
        back = set('aıou')
        res = ''
        last_vowel = None
        for ch in s:
            res += ch
            if ch in front or ch in back:
                last_vowel = ch
            elif ch.isalpha():
                v = last_vowel if last_vowel in front or last_vowel in back else 'e'
                res += v
        return res

    def _apply_hebrew_grammar(self, s: str) -> str:
        res = ''
        for ch in s:
            res += ch
            if re.match(r'[א-ת]', ch):
                res += 'a'
        return res

    def _apply_latin_grammar(self, s: str) -> str:
        vowels = 'aeiou'
        res = ''
        prev_vowel = False
        for ch in s:
            res += ch
            if ch.lower() not in vowels:
                if not prev_vowel:
                    res += 'i'
                prev_vowel = False
            else:
                prev_vowel = True
        return res

    def generate_name(self, number: Union[int, str], htype: str = 'ulvi', method: int = 1,
                      language: str = 'arabic', mode: str = 'regular') -> str:
        language = language.lower()
        htype = htype.upper()
        self._current_mode = mode  # store mode for use in generation
        suffix_map = {
            'arabic': {'ULVI':'ئيل','SUFLI':'يوش','ŞER':'طيش'},
            'hebrew': {'ULVI':'אל','SUFLI':'וש','ŞER':'טש'},
            'english': {'ULVI':'el','SUFLI':'us','ŞER':'is'},
            'latin': {'ULVI':'el','SUFLI':'us','ŞER':'is'},
            'turkish': {'ULVI':'el','SUFLI':'uş','ŞER':'iş'}
        }
        self._current_suffix = suffix_map.get(language, {}).get(htype, '')
        self._current_method = method
        suffix_val = abjad(self._current_suffix, method, 1, 0, language) if self._current_suffix else 0
        num = int(number)
        while suffix_val >= num:
            num += 361
        prefix = str(num - suffix_val)
        hpart: Dict[int, str] = {}
        counts = 0
        departs = len(prefix)
        while departs > 0:
            start = max(departs-3, 0)
            counts += 1
            hpart[counts] = prefix[start:departs]
            departs -= 3
        if language == 'arabic':
            return self.generate_arabic_name(hpart, counts, method, mode)
        elif language == 'hebrew':
            return self.generate_hebrew_name(hpart, counts)
        elif language == 'english':
            return self.generate_english_name(hpart, counts)
        elif language == 'latin':
            return self.generate_latin_name(hpart, counts)
        elif language == 'turkish':
            return self.generate_turkish_name(hpart, counts)
        else:
            return ''

	def calculate_abjad_value(self, text: str, method: int, mapping: Dict[str, int]) -> int:
		value = 0
		chars = re.findall(r'.', text, re.UNICODE)
		for char in chars:
			value += mapping.get(char, 0)
		return value

	def get_language_mappings(self) -> Dict[str, Dict[int, Dict[str, int]]]:
		return self.mappings

	def rakamtopla(self, valuez: Union[int, str], amount: int = 0) -> Union[str, int]:
		try:
			valuez = str(valuez)
			if amount == 0:
				hepsi = valuez
				while len(str(valuez)) > 1:
					newsum = sum(int(c) for c in str(valuez))
					valuez = str(newsum)
				return f"{hepsi} ► {valuez}"
			else:
				while len(str(valuez)) > amount:
					newsum = sum(int(c) for c in str(valuez))
					valuez = str(newsum)
				return int(valuez)
		except Exception as e:
			return f"Error: {str(e)}"

	def teksir(self, metin: str, ayrac: str = " ", shadda: int = 1) -> str:
		try:
			newmetin = self.saf(metin, 0, shadda)
			result = self.saf(newmetin, ayrac) + "\n"
			iksir = newmetin
			lengthdouble = 0

			if len(newmetin) % 2 == 0:
				lengthdouble = 1

			for _ in range(1, len(newmetin)):
				iksir = ""
				for counter in range(math.floor(len(newmetin) / 2)):
					inverse = len(newmetin) - counter - 1
					iksir += newmetin[inverse] + newmetin[counter]
				if lengthdouble != 1:
					iksir += newmetin[math.floor(len(newmetin) / 2)]

				result += self.saf(iksir, ayrac) + "\n"
				newmetin = self.saf(iksir, 0)

			return result
		except Exception as e:
			return f"Error: {str(e)}"

	def indian(self, metin: str) -> str:
		try:
			na = ""
			chars = re.findall(r'.', metin, re.UNICODE)
			num_map = {
				"0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤",
				"5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩"
			}

			for char in chars:
				na += num_map.get(char, char if char != " " else " ")

			return na
		except Exception as e:
			return f"Error: {str(e)}"

	def arabic(self, metin: str) -> str:
		try:
			na = ""
			chars = re.findall(r'.', metin, re.UNICODE)
			num_map = {
				"٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
				"٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"
			}

			for char in chars:
				na += num_map.get(char, char if char != " " else " ")

			return na
		except Exception as e:
			return f"Error: {str(e)}"