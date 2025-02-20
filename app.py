import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from werkzeug.utils import secure_filename
import io
import json

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Import models after db initialization to avoid circular imports
from models import Invoice, InvoiceItem, CompanyDetails

# Create upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def dashboard():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template('dashboard.html', invoices=invoices)

@app.route('/company-settings', methods=['GET', 'POST'])
def company_settings():
    company = CompanyDetails.query.first()

    if request.method == 'POST':
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        if company is None:
            company = CompanyDetails()

        company.company_name = request.form['company_name']
        company.email = request.form['email']
        company.address = request.form['address']
        company.phone = request.form['phone']

        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join('uploads', filename)
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(full_path)
                company.logo_path = file_path

        db.session.add(company)
        db.session.commit()
        flash('Company settings updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('company_settings.html', company=company)

@app.route('/create_invoice', methods=['GET', 'POST'])
def create_invoice():
    company = CompanyDetails.query.first()
    if request.method == 'POST':
        data = request.form

        invoice = Invoice(
            customer_name=data['customer_name'],
            customer_email=data['customer_email'],
            customer_address=data['customer_address'],
            total_amount=float(data['total_amount']),
            tax_amount=float(data['tax_amount']),
            tax_rate=float(data['tax_rate']),
            company_details_id=company.id if company else None,
            created_at=datetime.utcnow()  # Explicitly set the creation time
        )
        db.session.add(invoice)
        db.session.flush()

        items = json.loads(data['items'])
        for item in items:
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                description=item['description'],
                quantity=int(item['quantity']),
                unit_price=float(item['price']),
                subtotal=float(item['subtotal'])
            )
            db.session.add(invoice_item)

        db.session.commit()
        flash('Invoice created successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_invoice.html', company_details=company)

@app.route('/invoice/<int:invoice_id>')
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('view_invoice.html', invoice=invoice)

@app.route('/invoice/<int:invoice_id>/pdf')
def generate_pdf(invoice_id):
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        buffer = io.BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Add company logo if available
        if invoice.company_details and invoice.company_details.logo_path:
            logo_path = os.path.join(app.root_path, 'static', invoice.company_details.logo_path)
            if os.path.exists(logo_path):
                img = Image(logo_path, width=2*inch, height=1*inch)
                elements.append(img)
                elements.append(Spacer(1, 20))

        # Add title
        elements.append(Paragraph("INVOICE", styles['Title']))
        elements.append(Spacer(1, 20))

        # Company Details if available
        if invoice.company_details:
            company_info = [
                [Paragraph("Company Details:", styles['Heading2'])],
                [invoice.company_details.company_name],
                [invoice.company_details.address],
                [f"Phone: {invoice.company_details.phone}"],
                [f"Email: {invoice.company_details.email}"]
            ]
            company_table = Table(company_info, colWidths=[500])
            company_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(company_table)
            elements.append(Spacer(1, 20))

        # Customer Details
        customer_info = [
            [Paragraph("Customer Details:", styles['Heading2'])],
            ["Name:", invoice.customer_name],
            ["Email:", invoice.customer_email],
            ["Address:", invoice.customer_address],
            ["Date:", invoice.created_at.strftime('%Y-%m-%d') if invoice.created_at else 'N/A'],
            ["Invoice #:", str(invoice.id)]
        ]
        customer_table = Table(customer_info, colWidths=[100, 400])
        customer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 20))

        # Items Table
        items_data = [['Description', 'Quantity', 'Unit Price', 'Subtotal']]
        for item in invoice.items:
            items_data.append([
                item.description,
                str(item.quantity),
                f"Rs. {float(item.unit_price):.2f}",
                f"Rs. {float(item.subtotal):.2f}"
            ])

        # Add tax and total rows
        items_data.extend([
            ['', '', f'Tax ({float(invoice.tax_rate)*100:.0f}%):', f"Rs. {float(invoice.tax_amount):.2f}"],
            ['', '', 'Total:', f"Rs. {float(invoice.total_amount):.2f}"]
        ])

        items_table = Table(items_data, colWidths=[250, 75, 100, 100])
        items_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('LINEBELOW', (0, -2), (-1, -1), 1, colors.black),
            ('FONTNAME', (-2, -2), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (-2, -2), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(items_table)

        # Generate PDF
        doc.build(elements)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"invoice_{invoice_id}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        app.logger.error(f"Error generating PDF for invoice {invoice_id}: {str(e)}")
        flash('Error generating PDF. Please try again.', 'error')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)