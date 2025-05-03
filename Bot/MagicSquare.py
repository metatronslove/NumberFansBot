import math
from .NumberConverter import NumberConverter

class MagicSquareGenerator:
	def __init__(self):
		self.number_converter = NumberConverter()

	def generate_magic_square(self, n, row_sum=None, rotation=0, mirror=False, output_format="arabic"):
		if n < 3:
			return "Error: Size must be at least 3"
		magic_constant = (n * (n * n + 1)) / 2
		if row_sum is None:
			row_sum = magic_constant
		if row_sum < magic_constant:
			return f"Error: Row sum cannot be less than the magic constant ({magic_constant})"
		magic_square = self.create_magic_square(n)
		if row_sum > magic_constant:
			if n % 2 == 1:
				magic_square = self.incremented_magic_square(magic_square, row_sum)
			elif n % 4 == 0:
				magic_square = self.increment_matrix(magic_square, row_sum)
		if rotation > 0:
			magic_square = self.rotate_matrix(magic_square, rotation // 90)
		if mirror:
			magic_square = self.mirror_flip(magic_square)
		if output_format == "indian":
			magic_square = [
				[self.number_converter.indian(str(cell)) for cell in row]
				for row in magic_square
			]
		if not self.check_magic_square(magic_square, row_sum):
			return self.generate_magic_square((n + 1), row_sum, rotation, mirror, output_format)
		return {"box": self.box_the_square(magic_square, 4, 1, 1, output_format), "size": n}

	def create_magic_square(self, n):
		if n % 2 == 1:
			return self.siamese_method(n)
		elif n % 4 == 0:
			return self.strachey_method(n)
		else:
			return self.strachey_singly_even_method(n)

	def siamese_method(self, n):
		magic_square = [[0] * n for _ in range(n)]
		row, col = 0, n // 2
		for num in range(1, n * n + 1):
			magic_square[row][col] = int(num)
			next_row = (row - 1 + n) % n
			next_col = (col + 1) % n
			if magic_square[next_row][next_col] != 0:
				row = (row + 1) % n
			else:
				row, col = next_row, next_col
		return magic_square

	def strachey_method(self, n):
		magic_square = [[0] * n for _ in range(n)]
		count = 1
		for i in range(n):
			for j in range(n):
				if i % 4 == j % 4 or (i + j) % 4 == 3:
					magic_square[i][j] = int(n * n - count + 1)
				else:
					magic_square[i][j] = int(count)
				count += 1
		return magic_square

	def strachey_singly_even_method(self, n):
		magic_square = [[0] * n for _ in range(n)]
		k = n // 2
		mini_magic = self.siamese_method(k)
		for i in range(k):
			for j in range(k):
				magic_square[i][j] = int(mini_magic[i][j])
				magic_square[i + k][j + k] = int(mini_magic[i][j] + k * k)
				magic_square[i][j + k] = int(mini_magic[i][j] + 2 * k * k)
				magic_square[i + k][j] = int(mini_magic[i][j] + 3 * k * k)
		swap_col = list(range((k - 1) // 2)) + list(range(n - (k - 1) // 2 + 1, n))
		for i in range(k):
			for col in swap_col:
				magic_square[i][col], magic_square[i + k][col] = (
					magic_square[i + k][col], magic_square[i][col]
				)
		half_k = k // 2
		magic_square[half_k][0], magic_square[half_k + k][0] = (
			magic_square[half_k + k][0], magic_square[half_k][0]
		)
		magic_square[half_k + k][half_k], magic_square[half_k][half_k] = (
			magic_square[half_k][half_k], magic_square[half_k + k][half_k]
		)
		return magic_square

	def incremented_magic_square(self, magic_square, row_sum):
		n = len(magic_square)
		magic_constant = (n * (n * n + 1)) / 2
		incremention = (row_sum - magic_constant) / n
		for r in range(n):
			for c in range(n):
				magic_square[r][c] += self.incremention_for_cell(
					n, row_sum, incremention, magic_square[r][c]
				)
		return magic_square

	def incremention_for_cell(self, n, row_sum, incremention, cell_value):
		magic_constant = (n * (n * n + 1)) / 2
		threshold = n * n - n * (row_sum % n)
		return math.ceil(incremention) if cell_value > threshold else math.floor(incremention)

	def increment_matrix(self, magic_square, row_sum):
		n = len(magic_square)
		magic_constant = (n * (n * n + 1)) / 2
		z = (row_sum - magic_constant) % n
		incremention = (row_sum - magic_constant - z) / n
		for k in range(int(z)):
			for i in range(n):
				row = (k + i) % n
				col = i
				magic_square[row][col] += 1
		for r in range(n):
			for c in range(n):
				magic_square[r][c] += incremention
		return magic_square

	def mirror_flip(self, magic_square):
		n = len(magic_square)
		mirror_flipped = [[0] * n for _ in range(n)]
		for a in range(n):
			for b in range(n):
				m = n - 1 - a
				n_idx = n - 1 - b
				mirror_flipped[a][b] = magic_square[m][n_idx]
		return mirror_flipped

	def rotate_matrix(self, matrix, repeat):
		n = len(matrix)
		rotated = [[matrix[i][j] for j in range(n)] for i in range(n)]
		for _ in range(repeat % 4):  # Normalize rotations
			temp = [[0] * n for _ in range(n)]
			for i in range(n):
				for j in range(n):
					temp[i][j] = rotated[i][j]
			for i in range(n):
				for j in range(n):
					rotated[j][n - 1 - i] = temp[i][j]
		return rotated

	def box_the_square(self, magic_square, border_style=0, cell_height=1, cell_width=0, number_format="arabic"):
		box = [
			["─", "│", "┌", "┐", "└", "┘", "├", "┼", "┤", "┬", "┴"],
			["┄", "┆", "┌", "┐", "└", "┘", "├", "┼", "┤", "┬", "┴"],
			["┅", "┇", "┏", "┓", "┗", "┛", "┣", "╋", "┫", "┳", "┻"],
			["─", "│", "╭", "╮", "╰", "╯", "├", "┼", "┤", "┬", "┴"],
			["━", "┃", "┏", "┓", "┗", "┛", "┣", "╋", "┫", "┳", "┻"],
			["═", "║", "╔", "╗", "╚", "╝", "╠", "╬", "╣", "╦", "╩"],
		]
		border_style = max(0, min(border_style, len(box) - 1))
		n = len(magic_square)
		longest_length = 0
		for row in magic_square:
			for cell in row:
				value = str(cell)
				if number_format == "indian":
					value = self.number_converter.indian(value)
				length = len(value.replace("\u200e", "").replace("\u200f", ""))
				longest_length = max(longest_length, length)
		cell_width = max(cell_width, longest_length)
		border_length = cell_width
		length_for_num = cell_width + 2 if number_format == "indian" else cell_width
		cell_height = max(1, cell_height)
		boxed = []

		for r in range(n):
			if r == 0:
				line = (box[border_style][2] +
						''.join(box[border_style][0] * border_length + box[border_style][9] for _ in range(n - 1)) +
						box[border_style][0] * border_length + box[border_style][3])
				boxed.append(line)

			for e in range((cell_height - 1) // 2):
				line = box[border_style][1] + ''.join(" " * border_length + box[border_style][1] for _ in range(n))
				boxed.append(line)

			line = box[border_style][1]
			for c in range(n):
				cell_value = magic_square[r][c]
				display_value = (f"\u200e\u200f{self.number_converter.arab_to_indian(cell_value)}\u200e"
								if number_format == "indian" and not isinstance(cell_value, str)
								else str(cell_value))
				value_length = len(display_value.replace("\u200e", "").replace("\u200f", ""))
				padding = border_length - value_length
				left_pad = padding // 2
				right_pad = padding - left_pad
				line += " " * left_pad + display_value + " " * right_pad + box[border_style][1]
			boxed.append(line)

			for e in range(cell_height - 1 - (cell_height - 1) // 2):
				line = box[border_style][1] + ''.join(" " * border_length + box[border_style][1] for _ in range(n))
				boxed.append(line)

			if r < n - 1:
				line = (box[border_style][6] +
						''.join(box[border_style][0] * border_length + box[border_style][7] for _ in range(n - 1)) +
						box[border_style][0] * border_length + box[border_style][8])
				boxed.append(line)
			else:
				line = (box[border_style][4] +
						''.join(box[border_style][0] * border_length + box[border_style][10] for _ in range(n - 1)) +
						box[border_style][0] * border_length + box[border_style][5])
				boxed.append(line)

		return "\n".join(boxed)

	def check_magic_square(self, magic_square, expected_sum):
		n = len(magic_square)
		expected_sum = int(expected_sum)  # Ensure expected_sum is integer
		for i in range(n):
			row_sum = sum(int(float(cell)) if str(cell).replace('.', '').isdigit() else 0 for cell in magic_square[i])
			if row_sum != expected_sum:
				return False
		for j in range(n):
			col_sum = sum(int(float(magic_square[i][j])) if str(magic_square[i][j]).replace('.', '').isdigit() else 0 for i in range(n))
			if col_sum != expected_sum:
				return False
		diag_sum1 = sum(int(float(magic_square[i][i])) if str(magic_square[i][i]).replace('.', '').isdigit() else 0 for i in range(n))
		if diag_sum1 != expected_sum:
			return False
		diag_sum2 = sum(int(float(magic_square[i][n - 1 - i])) if str(magic_square[i][n - 1 - i]).replace('.', '').isdigit() else 0 for i in range(n))
		if diag_sum2 != expected_sum:
			return False
		return True