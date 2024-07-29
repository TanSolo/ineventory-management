import csv
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from io import BytesIO, StringIO

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for flashing messages
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
db = SQLAlchemy(app)


class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reorder_point = db.Column(db.Integer, nullable=False)
    visible = db.Column(db.Boolean, default=True, nullable=False)


def parse_quantity(quantity_str):
    """ Convert shorthand notation like 10k to integer """
    quantity_str = quantity_str.lower().replace(',', '')
    if 'k' in quantity_str:
        return int(float(quantity_str.replace('k', '')) * 1000)
    if 'm' in quantity_str:
        return int(float(quantity_str.replace('m', '')) * 1000000)
    if 'b' in quantity_str:
        return int(float(quantity_str.replace('b', '')) * 1000000000)
    return int(quantity_str)


@app.route('/')
def index():
    search = request.args.get('search')
    if search:
        items = InventoryItem.query.filter(InventoryItem.name.contains(search)).all()
        for item in items:
            item.visible = True
        invisible_items = InventoryItem.query.filter(~InventoryItem.name.contains(search)).all()
        for item in invisible_items:
            item.visible = False
    else:
        items = InventoryItem.query.all()
        for item in items:
            item.visible = True
    return render_template('index.html', items=items)


@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        quantity = parse_quantity(request.form['quantity'])
        reorder_point = parse_quantity(request.form['reorder_point'])
        new_item = InventoryItem(name=name, quantity=quantity, reorder_point=reorder_point)
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_item.html')


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_item(id):
    item = InventoryItem.query.get_or_404(id)
    if request.method == 'POST':
        item.name = request.form['name']
        item.quantity = parse_quantity(request.form['quantity'])
        item.reorder_point = parse_quantity(request.form['reorder_point'])
        db.session.commit()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('edit_item.html', item=item)


@app.route('/delete/<int:id>', methods=['POST'])
def delete_item(id):
    item = InventoryItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/export')
def export_csv():
    items = InventoryItem.query.all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Name', 'Quantity', 'Reorder Point'])
    for item in items:
        writer.writerow([item.id, item.name, item.quantity, item.reorder_point])

    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='text/csv', attachment_filename='inventory.csv', as_attachment=True)


@app.route('/import', methods=['GET', 'POST'])
def import_csv():
    if request.method == 'POST':
        file = request.files['file']
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.reader(stream)
        next(reader)  # Skip the header row
        for row in reader:
            new_item = InventoryItem(name=row[1], quantity=row[2], reorder_point=row[3])
            db.session.add(new_item)
        db.session.commit()
        flash('Data imported successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('import.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
