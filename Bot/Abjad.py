import re
import math
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
			char = chars[i]
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
			if detail:
				details.append({"char": char, "value": value})

			i += 1

		return {"sum": sum_value, "details": details} if detail else sum_value

	def bastet(self, metin: str, mt: int, tablo: int = 1, shadda: int = 1, language: str = "ARABIC", detail: int = 0) -> str:
		try:
			err = 0
			language = language.upper()

			if metin.isdigit():
				baster = int(metin)
			else:
				if 0 <= tablo <= 15:
					baster = self.abjad(metin, tablo, shadda)
				elif -16 <= tablo < 0:
					invertablo = -tablo - 1
					baster = self.abjad(metin, invertablo, shadda)

			for _ in range(mt):
				ns = self.nutket(baster, language)
				baster = 0

				if 0 <= tablo <= 15:
					baster = self.abjad(ns, tablo, 1) + self.abjad(ns, 5, 1)
				elif -16 <= tablo < 0:
					baster = self.abjad(ns, invertablo, 1)
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

	def nutket(self, mynumber: Union[int, str], language: str = "ARABIC", gender: str = "male") -> str:
		try:
			spell = ""
			count = 0
			language = language.upper()
			gender = gender.lower()

			if mynumber == 0:
				return {
					"ARABIC": "صفر",
					"HEBREW": "אֶפֶס",
					"LATIN": "nulla",
					"ENGLISH": "zero",
					"TURKISH": "sıfır"
				}.get(language, "zero")

			mynumber = str(mynumber)

			if language == "ARABIC":
				place_ones = ["", "ألف", "مليون", "مليار", "تريليون"]
				place_twos = ["", "ألفان", "مليونان", "ملياران", "تريليونان"]
				place_appent = ["", "ألفاً", "مليوناً", "ملياراً", "تريليوناً"]
				place_plural = ["", "آلاف", "ملايين", "مليارات", "تريليونات"]

				while mynumber:
					event_happenned = 0
					last_three = mynumber[-3:] if len(mynumber) >= 3 else mynumber
					last_three_float = float(last_three)

					if count > 0 and last_three_float == 1:
						temp = ""
						spell = f"{place_ones[count]} {'و ' if spell else ''}{spell}"
					elif count > 0 and last_three_float == 2:
						temp = ""
						spell = f"{place_twos[count]} {'و ' if spell else ''}{spell}"
					else:
						temp = self.get_hundreds(last_three, language, count, spell, gender)

					if temp:
						if count > 0:
							if spell:
								spell = f" و {spell}"
							if last_three_float != 2 and math.floor(last_three_float / 100) != 1:
								if 3 <= last_three_float <= 10:
									spell = f" {place_plural[count]}{spell}"
									event_happenned = 1
						if not event_happenned:
							spell = f" {place_appent[count] if spell else place_ones[count]}{spell}"
						spell = temp + spell
						temp = ""

					mynumber = mynumber[:-3] if len(mynumber) > 3 else ""
					count += 1

			# Similar implementations for HEBREW, LATIN, ENGLISH, TURKISH
			# (Omitted for brevity, but follow similar structure)

			return spell.strip()
		except Exception as e:
			return f"Error: {str(e)}"

	def get_hundreds(self, mynumber: str, language: str = "ARABIC", count: int = 0, spell: str = "", gender: str = "male") -> str:
		try:
			result = ""
			mynumber = f"{'0' * (3 - len(mynumber))}{mynumber}"[-3:]

			if language == "ARABIC":
				hundreds = int(mynumber[0])
				if hundreds > 0:
					if int(mynumber[1]) == 2 and int(mynumber[2]) == 0:
						result = "مئتان " if count == 0 else "مئتا "
					else:
						hundreds_map = {
							1: "مائة ", 2: "مئتان ", 3: "ثلاثمائة ", 4: "أربعمائة ",
							5: "خمسمائة ", 6: "ستمائة ", 7: "سبعمائة ", 8: "ثمانمائة ",
							9: "تسعمائة "
						}
						result = hundreds_map.get(hundreds, "")

				if result and int(mynumber[1:]) != 0:
					result += " و "

				if mynumber[1] != "0":
					result += self.get_tens(mynumber[1:], language, count, hundreds, result + spell, gender)
				else:
					result += self.get_digit(mynumber[2], language, count, result + spell, gender)

			# Similar implementations for other languages
			return result
		except Exception as e:
			return f"Error: {str(e)}"

	def get_tens(self, tenstext: str, language: str = "ARABIC", count: int = 0, hundreds: int = 0, spell: str = "", gender: str = "male") -> str:
		try:
			result = ""
			if language == "ARABIC":
				tens = int(tenstext[0])
				units = int(tenstext[1])
				number = int(tenstext)

				if tens == 1:
					tens_map = {
						10: "عشر" if gender == "female" else "عشرة",
						11: "إحدى عشر" if gender == "female" else "إحدى عشرة",
						12: "اثنتا عشر" if gender == "female" else "اثنتا عشرة",
						13: "ثلاث عشر" if gender == "female" else "ثلاث عشرة",
						14: "أربع عشر" if gender == "female" else "أربع عشرة",
						15: "خمس عشر" if gender == "female" else "خمس عشرة",
						16: "ست عشر" if gender == "female" else "ست عشرة",
						17: "سبع عشر" if gender == "female" else "سبع عشرة",
						18: "ثمان عشر" if gender == "female" else "ثمان عشرة",
						19: "تسع عشر" if gender == "female" else "تسع عشرة"
					}
					result = tens_map.get(number, "")
				else:
					tens_map = {
						2: "عشرون ", 3: "ثلاثون ", 4: "أربعون ", 5: "خمسون ",
						6: "ستون ", 7: "سبعون ", 8: "ثمانون ", 9: "تسعون "
					}
					result = tens_map.get(tens, "")
					if units != 0:
						result = self.get_digit(str(units), language, count, spell, gender) + " و " + result

			return result
		except Exception as e:
			return f"Error: {str(e)}"

	def get_digit(self, digit: str, language: str = "ARABIC", count: int = 0, spell: str = "", gender: str = "male") -> str:
		try:
			digit = int(digit)
			if language == "ARABIC":
				digit_map = {
					1: "واحد" if gender == "male" else "واحدة",
					2: "اثنان" if gender == "male" else "اثنتان",
					3: "ثلاثة" if count == 0 else "ثلاث",
					4: "أربعة" if count == 0 else "أربع",
					5: "خمسة" if count == 0 else "خمس",
					6: "ستة" if count == 0 else "ست",
					7: "سبعة" if count == 0 else "سبع",
					8: "ثمانية" if count == 0 else "ثمان",
					9: "تسعة" if count == 0 else "تسع"
				}
				return digit_map.get(digit, "")
			return ""
		except Exception as e:
			return f"Error: {str(e)}"

	def generate_name(self, prefix: Union[str, int], htype: str, method: int = 1, language: str = "arabic", mode: str = "regular") -> str:
		try:
			prefix = str(prefix)
			hpart = {}
			counts = 0

			if len(prefix) > 3:
				departs = len(prefix)
				counts = 0
				while departs > 0:
					hpart[counts + 1] = prefix[max(departs - 3, 0):departs]
					departs -= 3
					counts += 1
				if hpart[counts][-1] == "0":
					counts -= 1
			else:
				hpart[1] = prefix
				counts = 1

			language = language.lower()
			gh = ""
			if language == "arabic":
				gh = self.generate_arabic_name(hpart, counts, method, mode)
				if method in [1, 7, 12, 17, 22, 27, 32]:
					gh += {"ULVI": "ئيل", "SUFLI": "يوش", "ŞER": "طيش", "ULVİ": "ئيل", "SUFLİ": "يوش", "SER": "طيش"}.get(htype.upper(), htype)
			elif language == "hebrew":
				gh = self.generate_hebrew_name(hpart, counts)
				gh += {"ULVI": "אל", "SUFLI": "וש", "ŞER": "טש", "ULVİ": "אל", "SUFLİ": "וש", "SER": "טש"}.get(htype.upper(), htype)
			elif language == "english":
				gh = self.generate_english_name(hpart, counts)
				gh += {"ULVI": "el", "SUFLI": "us", "ŞER": "is", "ULVİ": "el", "SUFLİ": "us", "SER": "is"}.get(htype.upper(), htype.lower())
			elif language == "latin":
				gh = self.generate_latin_name(hpart, counts)
				gh += {"ULVI": "el", "SUFLI": "us", "ŞER": "is", "ULVİ": "el", "SUFLİ": "us", "SER": "is"}.get(htype.upper(), htype.lower())
			elif language == "turkish":
				gh = self.generate_turkish_name(hpart, counts)
				gh += {"ULVI": "el", "SUFLI": "uş", "ŞER": "iş", "ULVİ": "el", "SUFLİ": "uş", "SER": "iş"}.get(htype.upper(), htype.lower())

			return gh
		except Exception as e:
			return f"Error: {str(e)}"

	def generate_arabic_name(self, hpart: Dict[int, str], counts: int, method: int, mode: str) -> str:
		gh = ""
		eacher = ""

		for counter in range(counts, 0, -1):
			for counting in range(len(hpart[counter])):
				choosen = hpart[counter][counting]
				turn = 4 - len(hpart[counter]) + counting

				h = ""
				if turn == 3:
					if choosen == "1":
						h = "ا" if len(hpart[counter]) > 1 or counts == 1 else ""
					elif choosen == "2":
						h = "ل" if method == 12 else "ب"
					elif choosen == "3":
						h = "ن" if method == 12 else "ت" if method in [17, 22, 27, 32] else "ج"
					# Add other cases similarly
				elif turn == 2:
					# Implement similar logic
					pass
				elif turn == 1:
					# Implement similar logic
					pass

				if h:
					gh += h

				eacher = ""
				for counted in range(1, counter):
					eacher += {"7": "ش", "12": "ظ", "1": "غ"}.get(str(method), "ي" if method in [17, 22, 27, 32] else "غ")

				if mode == "eacher":
					gh += eacher
					eacher = ""

			if mode == "regular":
				gh += eacher

		return gh

	def generate_hebrew_name(self, hpart: Dict[int, str], counts: int) -> str:
		gh = ""
		hebrew_chars = {"1": "א", "2": "ב", "3": "ג", "4": "ד", "5": "ה", "6": "ו", "7": "ז", "8": "ח", "9": "ט", "0": "י"}

		for counter in range(counts, 0, -1):
			part_name = ""
			for counting in range(len(hpart[counter])):
				choosen = hpart[counter][counting]
				part_name += hebrew_chars.get(choosen, "")
			gh += self.ensure_hebrew_readability(part_name)

		return gh

	def ensure_hebrew_readability(self, name: str) -> str:
		vowels = ["א", "ה", "ו", "י"]
		has_vowel = any(char in vowels for char in name)

		if not has_vowel and name:
			return name[0] + "א" + name[1:]
		return name

	def generate_english_name(self, hpart: Dict[int, str], counts: int) -> str:
		gh = ""
		english_chars = {"1": "a", "2": "b", "3": "c", "4": "d", "5": "e", "6": "f", "7": "g", "8": "h", "9": "i", "0": "j"}
		syllables = ["an", "ar", "ba", "be", "bi", "bo", "ca", "ce", "ch", "co", "da", "de", "di", "do", "el", "en", "er", "es", "et", "fa", "fe", "fi", "fo", "ga", "ge", "gi", "go", "ha", "he", "hi", "ho", "in", "is", "it", "ja", "je", "ji", "jo", "ka", "ke", "ki", "ko", "la", "le", "li", "lo", "ma", "me", "mi", "mo", "na", "ne", "ni", "no", "on", "or", "pa", "pe", "pi", "po", "ra", "re", "ri", "ro", "sa", "se", "si", "so", "ta", "te", "ti", "to", "un", "ur", "va", "ve", "vi", "vo", "za", "ze", "zi", "zo"]

		for counter in range(counts, 0, -1):
			raw_name = "".join(english_chars.get(c, "") for c in hpart[counter])
			gh += self.ensure_english_readability(raw_name, syllables)

		return gh.capitalize()

	def ensure_english_readability(self, raw_name: str, syllables: List[str]) -> str:
		if len(raw_name) <= 2:
			return raw_name

		readable = ""
		vowels = "aeiou"
		has_vowel = any(c in vowels for c in raw_name)

		if not has_vowel:
			i = 0
			while i < len(raw_name):
				pair = raw_name[i:i+2]
				if len(pair) == 2:
					found = False
					for syllable in syllables:
						if syllable[0] == pair[0]:
							readable += syllable
							found = True
							break
					if not found:
						readable += pair[0] + "a"
				else:
					readable += raw_name[i] + "a"
				i += 2
		else:
			readable = raw_name

		return readable

	def generate_latin_name(self, hpart: Dict[int, str], counts: int) -> str:
		gh = ""
		latin_chars = {"1": "a", "2": "b", "3": "c", "4": "d", "5": "e", "6": "f", "7": "g", "8": "h", "9": "i", "0": "j"}
		syllables = ["am", "an", "ar", "as", "at", "em", "en", "er", "es", "et", "im", "in", "ir", "is", "it", "om", "on", "or", "os", "ot", "um", "un", "ur", "us", "ut", "ba", "be", "bi", "bo", "bu", "ca", "ce", "ci", "co", "cu", "da", "de", "di", "do", "du", "fa", "fe", "fi", "fo", "fu", "ga", "ge", "gi", "go", "gu", "la", "le", "li", "lo", "lu", "ma", "me", "mi", "mo", "mu", "na", "ne", "ni", "no", "nu", "pa", "pe", "pi", "po", "pu", "ra "re", "ri", "ro", "ru", "sa", "se", "si", "so", "su", "ta", "te", "ti", "to", "tu", "va", "ve", "vi", "vo", "vu"]
		endings = ["us", "um", "is", "ix", "ex", "ax", "or", "er", "io", "ius"]

		for counter in range(counts, 0, -1):
			raw_name = "".join(latin_chars.get(c, "") for c in hpart[counter])
			gh += self.ensure_latin_readability(raw_name, syllables)

		if not any(gh.endswith(end) for end in endings) and gh:
			gh += endings[random.randint(0, len(endings) - 1)]

		return gh.capitalize()

	def ensure_latin_readability(self, raw_name: str, syllables: List[str]) -> str:
		if len(raw_name) <= 2:
			return raw_name

		readable = ""
		vowels = "aeiou"
		has_vowel = any(c in vowels for c in raw_name)

		if not has_vowel:
			i = 0
			while i < len(raw_name):
				pair = raw_name[i:i+2]
				if len(pair) == 2:
					found = False
					for syllable in syllables:
						if syllable[0] == pair[0]:
							readable += syllable
							found = True
							break
					if not found:
						readable += pair[0] + "a"
				else:
					readable += raw_name[i] + "a"
				i += 2
		else:
			readable = raw_name

		return readable

	def generate_turkish_name(self, hpart: Dict[int, str], counts: int) -> str:
		gh = ""
		turkish_chars = {"1": "a", "2": "b", "3": "c", "4": "ç", "5": "d", "6": "e", "7": "f", "8": "g", "9": "ğ", "0": "h"}
		syllables = ["an", "ar", "as", "at", "ay", "ba", "be", "bi", "bo", "bu", "ca", "ce", "ci", "co", "cu", "ça", "çe", "çi", "ço", "çu", "da", "de", "di", "do", "du", "el", "em", "en", "er", "es", "et", "ev", "ey", "fa", "fe", "fi", "fo", "fu", "ga", "ge", "gi", "go", "gu", "ha", "he", "hi", "ho", "hu", "ık", "ıl", "ın", "ır", "iç", "il", "im", "in", "ir", "iş", "it", "iz", "ka", "ke", "ki", "ko", "ku", "la", "le", "li", "lo", "lu", "ma", "me", "mi", "mo", "mu", "na", "ne", "ni", "no", "nu", "ok", "ol", "on", "or", "oy", "pa", "pe", "pi", "po", "pu", "ra", "re", "ri", "ro", "ru", "sa", "se", "si", "so", "su", "şa", "şe", "şi", "şo", "şu", "ta", "te", "ti", "to", "tu", "ul", "um", "un", "ur", "ut", "uç", "uş", "üç", "ül", "ün", "üs", "üz", "va", "ve", "vi", "vo", "vu", "ya", "ye", "yi", "yo", "yu", "za", "ze", "zi", "zo", "zu"]

		for counter in range(counts, 0, -1):
			raw_name = "".join(turkish_chars.get(c, "") for c in hpart[counter])
			gh += self.ensure_turkish_readability(raw_name, syllables)

		return gh.capitalize()

	def ensure_turkish_readability(self, raw_name: str, syllables: List[str]) -> str:
		if len(raw_name) <= 2:
			return raw_name

		readable = ""
		vowels = "aeıioöuü"
		has_vowel = any(c in vowels for c in raw_name)

		if not has_vowel:
			i = 0
			while i < len(raw_name):
				pair = raw_name[i:i+2]
				if len(pair) == 2:
					found = False
					for syllable in syllables:
						if syllable[0] == pair[0]:
							readable += syllable
							found = True
							break
					if not found:
						readable += pair[0] + "a"
				else:
					readable += raw_name[i] + "a"
				i += 2
		else:
			readable = raw_name

		return self.apply_turkish_vowel_harmony(readable)

	def apply_turkish_vowel_harmony(self, name: str) -> str:
		front_vowels = "eiöü"
		back_vowels = "aıou"
		last_vowel = ""

		for char in reversed(name):
			if char in front_vowels + back_vowels:
				last_vowel = char
				break

		if not last_vowel:
			return name

		return name + ("i" if last_vowel in front_vowels else "ı")

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

	def arabic(self, metin: str) -> str:
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

	def indian(self, metin: str) -> str:
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