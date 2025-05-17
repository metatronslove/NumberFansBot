from flask import request, render_template, redirect, url_for, session, flash, jsonify
from datetime import datetime
from Bot.Helpers.papara_integration import PaparaPaymentManager

def register_payment_routes(flask_app, db, i18n, AVAILABLE_LANGUAGES):
	"""Register payment-related routes with the Flask application."""

	# Initialize payment manager
	payment_manager = PaparaPaymentManager(db)

	@flask_app.route("/<lang>/create_payment", methods=["POST"])
	def create_payment(lang="en"):
		"""Create a new payment request."""
		if "username" not in session:
			return jsonify({"success": False, "error": "Unauthorized"}), 401

		if lang not in AVAILABLE_LANGUAGES:
			lang = "en"

		try:
			data = request.get_json()
			amount = float(data.get("amount", 0))
			product_id = data.get("product_id")
			order_id = data.get("order_id")

			if amount <= 0:
				return jsonify({
					"success": False,
					"error": i18n.t("INVALID_AMOUNT", lang)
				})

			user_id = session.get("user_id")
			if not user_id:
				return jsonify({
					"success": False,
					"error": i18n.t("USER_NOT_FOUND", lang)
				})

			result = payment_manager.create_payment_request(user_id, amount, product_id, order_id)
			return jsonify(result)

		except Exception as e:
			return jsonify({
				"success": False,
				"error": str(e)
			})

	@flask_app.route("/<lang>/check_payment", methods=["POST"])
	def check_payment(lang="en"):
		"""Check if a payment has been received."""
		if "username" not in session:
			return jsonify({"success": False, "error": "Unauthorized"}), 401

		if lang not in AVAILABLE_LANGUAGES:
			lang = "en"

		try:
			data = request.get_json()
			description = data.get("description")

			if not description:
				return jsonify({
					"success": False,
					"error": i18n.t("MISSING_DESCRIPTION", lang)
				})

			payment_received = payment_manager.check_payment_status(description)
			return jsonify({
				"success": payment_received
			})

		except Exception as e:
			return jsonify({
				"success": False,
				"error": str(e)
			})

	@flask_app.route("/<lang>/cancel_payment", methods=["POST"])
	def cancel_payment(lang="en"):
		"""Cancel a pending payment."""
		if "username" not in session:
			return jsonify({"success": False, "error": "Unauthorized"}), 401

		if lang not in AVAILABLE_LANGUAGES:
			lang = "en"

		try:
			data = request.get_json()
			payment_id = data.get("payment_id")

			if not payment_id:
				return jsonify({
					"success": False,
					"error": i18n.t("MISSING_PAYMENT_ID", lang)
				})

			user_id = session.get("user_id")
			if not user_id:
				return jsonify({
					"success": False,
					"error": i18n.t("USER_NOT_FOUND", lang)
				})

			result = payment_manager.cancel_payment(payment_id, user_id)
			return jsonify(result)

		except Exception as e:
			return jsonify({
				"success": False,
				"error": str(e)
			})

	@flask_app.route("/<lang>/user_payments")
	def user_payments(lang="en"):
		"""Get all payments for the current user."""
		if "username" not in session:
			return redirect(url_for("login", lang=lang))

		if lang not in AVAILABLE_LANGUAGES:
			lang = "en"

		try:
			user_id = session.get("user_id")
			if not user_id:
				flash(i18n.t("USER_NOT_FOUND", lang), "error")
				return redirect(url_for("login", lang=lang))

			payments = payment_manager.get_user_payments(user_id)

			return render_template(
				"payments_partial.html",
				i18n=i18n,
				lang=lang,
				payments=payments
			)

		except Exception as e:
			flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")
			return redirect(url_for("user_dashboard", lang=lang))
