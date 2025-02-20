from app import db
from datetime import datetime
from sqlalchemy import Numeric

class CompanyDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    logo_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    tax_amount = db.Column(Numeric(10, 2), nullable=False)
    tax_rate = db.Column(Numeric(4, 2), nullable=False, server_default='0.10')  # Store as decimal (0.10 for 10%)
    company_details_id = db.Column(db.Integer, db.ForeignKey('company_details.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    company_details = db.relationship('CompanyDetails')

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(Numeric(10, 2), nullable=False)
    subtotal = db.Column(Numeric(10, 2), nullable=False)