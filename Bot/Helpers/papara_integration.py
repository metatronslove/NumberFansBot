import logging
import time
import os
import json
import imaplib
import email
from email.header import decode_header
from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)

class PaparaPaymentManager:
    def __init__(self, db_connection):
        self.db = db_connection
        self.payments = {}
        
    def generate_unique_description(self, user_id):
        """Generate a unique payment description for tracking purposes."""
        timestamp = int(time.time())
        return f"payment_{user_id}_{timestamp}"
    
    def create_payment_request(self, user_id, amount, product_id=None, order_id=None):
        """Create a new payment request and store it in the database."""
        description = self.generate_unique_description(user_id)
        
        # Store payment request in database
        try:
            query = """
                INSERT INTO payment_requests 
                (user_id, amount, description, product_id, order_id, status, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.db.cursor.execute(
                query, 
                (user_id, amount, description, product_id, order_id, 'pending', datetime.now())
            )
            payment_id = self.db.cursor.lastrowid
            self.db.conn.commit()
            
            # Cache payment info
            self.payments[description] = {
                'id': payment_id,
                'user_id': user_id,
                'amount': amount,
                'product_id': product_id,
                'order_id': order_id,
                'status': 'pending',
                'created_at': datetime.now()
            }
            
            return {
                'success': True,
                'payment_id': payment_id,
                'description': description
            }
        except Exception as e:
            logger.error(f"Error creating payment request: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_payment_status(self, description):
        """Check if a payment has been received for the given description."""
        try:
            # First check database for already confirmed payments
            query = "SELECT * FROM payment_requests WHERE description = %s"
            self.db.cursor.execute(query, (description,))
            payment = self.db.cursor.fetchone()
            
            if payment and payment['status'] == 'completed':
                return True
                
            # If not found or not completed, check email
            if self._check_email_for_payment(description):
                # Update payment status in database
                self._update_payment_status(description, 'completed')
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}")
            return False
    
    def _check_email_for_payment(self, description):
        """Check email inbox for payment confirmation from Papara."""
        try:
            # Get email credentials from database or config
            query = "SELECT * FROM users WHERE user_id = %s"
            user_id = self.payments.get(description, {}).get('user_id')
            
            if not user_id:
                # Try to get from database
                query = "SELECT user_id FROM payment_requests WHERE description = %s"
                self.db.cursor.execute(query, (description,))
                result = self.db.cursor.fetchone()
                if result:
                    user_id = result['user_id']
                else:
                    return False
            
            # Get user's email settings
            self.db.cursor.execute("SELECT email, email_password FROM users WHERE user_id = %s", (user_id,))
            user = self.db.cursor.fetchone()
            
            if not user or not user['email'] or not user['email_password']:
                logger.error(f"Missing email credentials for user {user_id}")
                return False
                
            email_user = user['email']
            email_pass = user['email_password']
            
            # Connect to email server
            mail = imaplib.IMAP4_SSL("imap.gmail.com")  # Adjust for other email providers
            mail.login(email_user, email_pass)
            mail.select('inbox')
            
            # Search for emails from Papara
            status, messages = mail.search(None, 'FROM', '"Papara <bilgi@papara.com>"')
            email_ids = messages[0].split()
            
            # Check most recent emails first (last 10)
            for email_id in reversed(email_ids[-10:] if len(email_ids) > 10 else email_ids):
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Check subject
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                # Look for payment confirmation emails
                if "Hesabına" in subject or "hesabında" in subject.lower():
                    # Extract email body
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == 'text/plain':
                                body = part.get_payload(decode=True).decode()
                                if description in body:
                                    mail.close()
                                    mail.logout()
                                    return True
                    else:
                        body = msg.get_payload(decode=True).decode()
                        if description in body:
                            mail.close()
                            mail.logout()
                            return True
            
            mail.close()
            mail.logout()
            return False
        except Exception as e:
            logger.error(f"Error checking email for payment: {str(e)}")
            return False
    
    def _update_payment_status(self, description, status):
        """Update payment status in database."""
        try:
            query = "UPDATE payment_requests SET status = %s, updated_at = %s WHERE description = %s"
            self.db.cursor.execute(query, (status, datetime.now(), description))
            self.db.conn.commit()
            
            # Update cache if exists
            if description in self.payments:
                self.payments[description]['status'] = status
                
            # If payment is completed, process the order
            if status == 'completed':
                payment_info = self.payments.get(description, {})
                product_id = payment_info.get('product_id')
                order_id = payment_info.get('order_id')
                user_id = payment_info.get('user_id')
                
                if not user_id:
                    # Try to get from database
                    query = "SELECT user_id, product_id, order_id FROM payment_requests WHERE description = %s"
                    self.db.cursor.execute(query, (description,))
                    result = self.db.cursor.fetchone()
                    if result:
                        user_id = result['user_id']
                        product_id = result['product_id']
                        order_id = result['order_id']
                
                # Process based on what was purchased
                if product_id:
                    self._process_product_purchase(user_id, product_id)
                elif order_id:
                    self._update_order_status(order_id, 'paid')
                else:
                    # Generic balance update
                    amount = payment_info.get('amount', 0)
                    self._update_user_balance(user_id, amount)
                    
            return True
        except Exception as e:
            logger.error(f"Error updating payment status: {str(e)}")
            return False
    
    def _process_product_purchase(self, user_id, product_id):
        """Process a product purchase after payment is confirmed."""
        try:
            # Get product details
            query = "SELECT * FROM products WHERE id = %s"
            self.db.cursor.execute(query, (product_id,))
            product = self.db.cursor.fetchone()
            
            if not product:
                logger.error(f"Product {product_id} not found")
                return False
                
            # Handle different product types
            product_type = product['type']
            
            if product_type == 'shipped':
                # Create order for physical product
                query = """
                    INSERT INTO orders 
                    (user_id, product_id, status, amount, created_at) 
                    VALUES (%s, %s, %s, %s, %s)
                """
                self.db.cursor.execute(
                    query, 
                    (user_id, product_id, 'pending_approval', product['price'], datetime.now())
                )
                self.db.conn.commit()
                
                # Update product quantity
                if product['quantity'] is not None:
                    new_quantity = max(0, product['quantity'] - 1)
                    self.db.cursor.execute(
                        "UPDATE products SET quantity = %s WHERE id = %s",
                        (new_quantity, product_id)
                    )
                    self.db.conn.commit()
                    
            elif product_type == 'downloadable':
                # Create download record
                query = """
                    INSERT INTO downloads 
                    (user_id, product_id, status, created_at) 
                    VALUES (%s, %s, %s, %s)
                """
                self.db.cursor.execute(
                    query, 
                    (user_id, product_id, 'available', datetime.now())
                )
                self.db.conn.commit()
                
            elif product_type == 'membership':
                # Get membership details
                duration = product.get('membership_duration', 'monthly')
                
                # Calculate expiration date
                if duration == 'weekly':
                    expiry_days = 7
                elif duration == 'monthly':
                    expiry_days = 30
                elif duration == 'annually':
                    expiry_days = 365
                else:  # lifetime
                    expiry_days = None
                    
                # Create or update membership
                if expiry_days:
                    query = """
                        INSERT INTO memberships 
                        (user_id, group_id, expires_at, created_at) 
                        VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL %s DAY), %s)
                        ON DUPLICATE KEY UPDATE 
                        expires_at = DATE_ADD(NOW(), INTERVAL %s DAY),
                        updated_at = %s
                    """
                    self.db.cursor.execute(
                        query, 
                        (user_id, product['group_id'], expiry_days, datetime.now(), expiry_days, datetime.now())
                    )
                else:
                    # Lifetime membership
                    query = """
                        INSERT INTO memberships 
                        (user_id, group_id, expires_at, created_at) 
                        VALUES (%s, %s, NULL, %s)
                        ON DUPLICATE KEY UPDATE 
                        expires_at = NULL,
                        updated_at = %s
                    """
                    self.db.cursor.execute(
                        query, 
                        (user_id, product['group_id'], datetime.now(), datetime.now())
                    )
                self.db.conn.commit()
                
            return True
        except Exception as e:
            logger.error(f"Error processing product purchase: {str(e)}")
            return False
    
    def _update_order_status(self, order_id, status):
        """Update order status after payment is confirmed."""
        try:
            query = "UPDATE orders SET status = %s, updated_at = %s WHERE id = %s"
            self.db.cursor.execute(query, (status, datetime.now(), order_id))
            self.db.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating order status: {str(e)}")
            return False
    
    def _update_user_balance(self, user_id, amount):
        """Update user balance after payment is confirmed."""
        try:
            # Check if user exists in balance table
            query = "SELECT balance FROM users WHERE user_id = %s"
            self.db.cursor.execute(query, (user_id,))
            user = self.db.cursor.fetchone()
            
            if user is not None:
                # Update existing balance
                new_balance = user['balance'] + amount
                query = "UPDATE users SET balance = %s WHERE user_id = %s"
                self.db.cursor.execute(query, (new_balance, user_id))
            else:
                # Insert new balance record
                query = "INSERT INTO users (user_id, balance) VALUES (%s, %s)"
                self.db.cursor.execute(query, (user_id, amount))
                
            self.db.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user balance: {str(e)}")
            return False
    
    def get_user_payments(self, user_id):
        """Get all payments for a specific user."""
        try:
            query = """
                SELECT pr.*, p.name as product_name, p.type as product_type 
                FROM payment_requests pr
                LEFT JOIN products p ON pr.product_id = p.id
                WHERE pr.user_id = %s
                ORDER BY pr.created_at DESC
            """
            self.db.cursor.execute(query, (user_id,))
            return self.db.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user payments: {str(e)}")
            return []
    
    def cancel_payment(self, payment_id, user_id):
        """Cancel a pending payment."""
        try:
            # Verify payment belongs to user and is still pending
            query = "SELECT * FROM payment_requests WHERE id = %s AND user_id = %s AND status = 'pending'"
            self.db.cursor.execute(query, (payment_id, user_id))
            payment = self.db.cursor.fetchone()
            
            if not payment:
                return {
                    'success': False,
                    'error': 'Payment not found or cannot be canceled'
                }
                
            # Update payment status
            query = "UPDATE payment_requests SET status = 'canceled', updated_at = %s WHERE id = %s"
            self.db.cursor.execute(query, (datetime.now(), payment_id))
            self.db.conn.commit()
            
            # Remove from cache if exists
            description = payment['description']
            if description in self.payments:
                self.payments[description]['status'] = 'canceled'
                
            return {
                'success': True
            }
        except Exception as e:
            logger.error(f"Error canceling payment: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
