from flask import Flask, render_template, request, redirect, session, flash
from flask_session import Session
# from flask_mysqldb import MySQL
import pymysql
from flaskext.mysql import MySQL
import yaml
from base64 import b64encode
from dataclasses import dataclass

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
db = yaml.load(open('credentials.yaml'), Loader=yaml.FullLoader)
mysql = None

userdb = MySQL(app, prefix="userdb", host=db['mysql_host'],
               user=db['mysql_user1'], password=db['mysql_password1'], db=db['login_db'])
mysql1 = MySQL(app, prefix="mysql1", host=db['mysql_host'],
               user=db['mysql_user1'], password=db['mysql_password1'], db=db['mysql_db'])
mysql2 = MySQL(app, prefix="mysql2", host=db['mysql_host'],
               user=db['mysql_user2'], password=db['mysql_password2'], db=db['mysql_db'])
mysql3 = MySQL(app, prefix="mysql3", host=db['mysql_host'],
               user=db['mysql_user3'], password=db['mysql_password3'], db=db['mysql_db'])


@dataclass
class User():
    name: str
    password: str
    role: str = None

# defining home route


@app.route('/', methods=['GET'])
def index():
    session["logged_in"] = False
    session.pop("user", None)
    return render_template('index.html')


@app.route('/', methods=['POST'])
def login():
    session["user"] = User(request.form['name'], request.form['password'])
    cursor = userdb.get_db().cursor()
    cursor.execute(
        "SELECT password, role FROM login_details WHERE name=%s", (session["user"].name,))
    userdb.get_db().commit()
    password = cursor.fetchone()
    cursor.close()
    if password is None:
        flash("Not a recognized user")
        session.pop("user", None)
        return render_template('index.html')
    elif(password[0] == session["user"].password):
        session["logged_in"] = True
        global mysql
        if(password[1] == "admin"):
            mysql = mysql1
        elif(password[1] == "Student"):
            mysql = mysql2
        else:
            mysql = mysql3
        return redirect('/tables')
    else:
        session.pop("user", None)
        flash("Wrong Password")
        return render_template('index.html')


@app.route('/logout', methods=['GET'])
def logout():
    session["logged_in"] = False
    session.pop("user", None)
    return redirect('/')

# directing to team page or tables page

# @app.route('/', methods=['POST'])
# def home_post():
#     x = request.form

#     if(x.get('edit')==None):
#         return redirect('/team')
#     else:
#         return redirect('/tables')


# rendering team_details page
@app.route('/team', methods=['GET'])
def team():
    return render_template('team_details.html')


# rendering the list of tables in the database
@app.route('/tables', methods=['GET'])
def tables():
    if session["logged_in"] == False:
        return redirect('/')
    args = request.args
    table_name = args.get('tableName', default=None, type=str)
    if table_name is None:
        cursor = mysql.get_db().cursor()
        cursor.execute("SHOW TABLES")

        tables = cursor.fetchall()
        cursor.close()
        table_names = []
        print(tables)
        for i in range(len(tables)):
            table_names.append(tables[i][0])

        cur = mysql.get_db().cursor()
        schema = []
        for table_name in table_names:
            cur.execute(f"SHOW COLUMNS FROM {table_name}")
            mysql.get_db().commit()
            schema.append(cur.fetchall())
        cur.close()

        # return render_template('display_entries.html', userDetails=table_data, table_col_names=TABLE_COLUMN_NAMES, table_name=table_name, EntriesOrSchema="Schema",
        #                     display_edit_buttons="NO",display_edit_fields="NO")
        TABLE_COLUMN_NAMES = ["Field", "Type", "Null", "Key"]
        return render_template('display_tables.html', table_names=table_names, schema=schema, table_col_names=TABLE_COLUMN_NAMES, len=len(table_names), len_col=len(TABLE_COLUMN_NAMES))
    else:
        try:
            cur = mysql.get_db().cursor()
            cur.execute(f"SELECT * FROM {table_name}")
            mysql.get_db().commit()
            table_data = cur.fetchall()
            cur.close()

            # if table_name == "alumni":
            #     img = bytes.fromhex(table_data[0][4].decode('ascii'))
            #     print(img)
                # img = b64encode(table_data[0][4]).decode('utf-8')

            cursor = mysql.get_db().cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s and TABLE_NAME=%s", ("alumni", table_name,))
            table_column_names_tuples = cursor.fetchall()
            TABLE_COLUMN_NAMES = []

            for dict in table_column_names_tuples:
                x = dict['COLUMN_NAME']
                TABLE_COLUMN_NAMES.append(x)

            cursor.close()

            if mysql == mysql1:
                return render_template('display_entries.html', userDetails=table_data, table_name=table_name, table_col_names=TABLE_COLUMN_NAMES, EntriesOrSchema="Entries",
                                       display_edit_buttons="ADMIN", display_edit_fields="NO")
            elif mysql == mysql2:
                return render_template('display_entries.html', userDetails=table_data, table_name=table_name, table_col_names=TABLE_COLUMN_NAMES, EntriesOrSchema="Entries",
                                       display_edit_buttons="STUDENT", display_edit_fields="NO")
            elif mysql == mysql3:
                return render_template('display_entries.html', userDetails=table_data, table_name=table_name, table_col_names=TABLE_COLUMN_NAMES, EntriesOrSchema="Entries",
                                       display_edit_buttons="EMP", display_edit_fields="NO")

            # return render_template('display_entries.html', userDetails=table_data, table_name=table_name, table_col_names=TABLE_COLUMN_NAMES, EntriesOrSchema="Entries",
            #                        display_edit_buttons="ADMIN", display_edit_fields="NO")

        except Exception as e:

            print(e)
            return render_template('errors.html', errorMessage="Table not defined")


# updating rendered output based on Operations button pressed.

@app.route('/tables/edit', methods=['POST'])
def tables_edit():
    if session["logged_in"] == False:
        return redirect('/')
    x = request.form
    pressed = None
    table_name = None

    # which button was pressed
    if(x.get('insert') == None):
        if(x.get('update') == None):
            if(x.get('delete') == None):
                pressed = 'rename'
            else:
                pressed = 'delete'
        else:
            pressed = 'update'
    else:
        pressed = 'insert'

    # finding column names
    table_name = x[pressed]
    print(mysql.get_db().cursor())
    cursor = mysql.get_db().cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s and TABLE_NAME=%s", ("alumni", table_name,))
    table_column_names_tuples = cursor.fetchall()
    TABLE_COLUMN_NAMES = []

    for dict in table_column_names_tuples:
        y = dict['COLUMN_NAME']
        TABLE_COLUMN_NAMES.append(y)

    # finding table
    cur = mysql.get_db().cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    mysql.get_db().commit()
    table_data = cur.fetchall()

    # updating rendered output based on the button pressed
    if(pressed == 'insert'):
        return render_template('display_entries.html', userDetails=table_data, table_col_names=TABLE_COLUMN_NAMES, table_name=table_name, EntriesOrSchema="Insert",
                               display_edit_buttons="NO", display_edit_fields="YES", op='insert')
    elif(pressed == 'update'):
        return render_template('display_entries.html', userDetails=table_data, table_col_names=TABLE_COLUMN_NAMES, table_name=table_name, EntriesOrSchema="Update",
                               display_edit_buttons="NO", display_edit_fields="YES", op='update')
    elif(pressed == 'delete'):
        return render_template('display_entries.html', userDetails=table_data, table_col_names=TABLE_COLUMN_NAMES, table_name=table_name, EntriesOrSchema="Delete",
                               display_edit_buttons="NO", display_edit_fields="YES", op='delete')
    elif(pressed == 'rename'):
        return render_template('display_entries.html', userDetails=table_data, table_col_names=TABLE_COLUMN_NAMES, table_name=table_name, EntriesOrSchema="Rename",
                               display_edit_buttons="NO", display_edit_fields="YES", op='rename')
    else:
        return render_template('errors.html')


# insert page render logic

@app.route('/tables/edit/insert', methods=['POST'])
def edit_insert():
    if session["logged_in"] == False:
        return redirect('/')
    x = request.form
    print(x)
    table_name = x['table_name']

    # Table Before Insertion
    cur = mysql.get_db().cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    mysql.get_db().commit()
    table_data_before = cur.fetchall()

    # getting column names
    cursor = mysql.get_db().cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s and TABLE_NAME=%s", ("alumni", table_name,))
    table_column_names_tuples = cursor.fetchall()
    TABLE_COLUMN_NAMES = []

    for dict in table_column_names_tuples:
        y = dict['COLUMN_NAME']
        TABLE_COLUMN_NAMES.append(y)

    # filling new values
    NEW_VALUES = []
    for col in TABLE_COLUMN_NAMES:
        NEW_VALUES.append(x[col])

    # making the query
    query = "INSERT INTO " + table_name+"(" + ", ".join(TABLE_COLUMN_NAMES) + \
        ") VALUES (" + \
        ", ".join(["%s" for _ in range(len(TABLE_COLUMN_NAMES))]) + ")"

    # executing query
    cur = mysql.get_db().cursor()
    try:
        cur.execute(query, NEW_VALUES)
        mysql.get_db().commit()

        # table after query execution
        cur = mysql.get_db().cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        mysql.get_db().commit()
        table_data_after = cur.fetchall()

        return render_template('tables_before_after.html', table_before=table_data_before, table_after=table_data_after, table_name=table_name,
                               table_col_names=TABLE_COLUMN_NAMES)
    except Exception as e:
        print(e)
        return render_template('errors.html', errorMessage="Input Error- Re-check your input against the schema.", errorDetails=e.args[1])


# update page render logic

@app.route('/tables/edit/update', methods=['POST'])
def edit_update():
    if session["logged_in"] == False:
        return redirect('/')
    x = request.form
    table_name = x['table_name']
    condition = x['condition']

    # Table Before Insertion
    cur = mysql.get_db().cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    mysql.get_db().commit()
    table_data_before = cur.fetchall()

    # getting column names
    cursor = mysql.get_db().cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s and TABLE_NAME=%s", ("alumni", table_name,))
    table_column_names_tuples = cursor.fetchall()
    TABLE_COLUMN_NAMES = []

    for dict in table_column_names_tuples:
        y = dict['COLUMN_NAME']
        TABLE_COLUMN_NAMES.append(y)

    # filling new values

    NEW_VALUES = []
    for i in range(len(TABLE_COLUMN_NAMES)):
        if(x[TABLE_COLUMN_NAMES[i]] == ""):
            TABLE_COLUMN_NAMES[i] = "remove"
        else:
            NEW_VALUES.append(x[TABLE_COLUMN_NAMES[i]])

    # changing column names depending on participation of fields
    NEW_COLUMN_NAMES = []
    for name in TABLE_COLUMN_NAMES:
        if(name != "remove"):
            NEW_COLUMN_NAMES.append(name)

    # statement clauses
    strings = []
    for i in range(len(NEW_COLUMN_NAMES)):
        y = NEW_COLUMN_NAMES[i]+"="+NEW_VALUES[i]
        strings.append(y)

    # making query
    query = "UPDATE "+table_name+" SET " + \
        ", ".join(strings) + " WHERE " + condition

    try:
        cur = mysql.get_db().cursor()
        cur.execute(query)
        mysql.get_db().commit()

        # table after query execution
        cur = mysql.get_db().cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        mysql.get_db().commit()
        table_data_after = cur.fetchall()

        return render_template('tables_before_after.html', table_before=table_data_before, table_after=table_data_after, table_name=table_name,
                               table_col_names=TABLE_COLUMN_NAMES)
    except:
        return render_template('errors.html', errorMessage="Update Error- Re-check your update value types/condition against the schema and current database entries.")


# delete page render logic

@app.route('/tables/edit/delete', methods=['POST'])
def edit_delete():
    if session["logged_in"] == False:
        return redirect('/')
    x = request.form
    table_name = x['table_name']
    condition = x['condition']

    # Table Before Insertion
    cur = mysql.get_db().cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    mysql.get_db().commit()
    table_data_before = cur.fetchall()

    # getting column names
    cursor = mysql.get_db().cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s and TABLE_NAME=%s", ("alumni", table_name,))
    table_column_names_tuples = cursor.fetchall()
    TABLE_COLUMN_NAMES = []

    for dict in table_column_names_tuples:
        y = dict['COLUMN_NAME']
        TABLE_COLUMN_NAMES.append(y)

    # making query
    query = "DELETE FROM "+table_name+" WHERE " + condition

    try:
        cur = mysql.get_db().cursor()
        cur.execute(query)
        mysql.get_db().commit()

        # table after query execution
        cur = mysql.get_db().cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        mysql.get_db().commit()
        table_data_after = cur.fetchall()

        return render_template('tables_before_after.html', table_before=table_data_before, table_after=table_data_after, table_name=table_name,
                               table_col_names=TABLE_COLUMN_NAMES)
    except:
        return render_template('errors.html', errorMessage="Delete Error- Re-check your delete condition against the schema and current database entries.")


# rename page render logic

@app.route('/tables/edit/rename', methods=['POST'])
def edit_rename():
    if session["logged_in"] == False:
        return redirect('/')
    x = request.form
    old_table_name = x['table_name']
    new_table_name = x['new_table_name']

    # Table Before Insertion
    cur = mysql.get_db().cursor()
    cur.execute(f"SELECT * FROM {old_table_name}")
    mysql.get_db().commit()
    table_data_before = cur.fetchall()

    # getting column names
    cursor = mysql.get_db().cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s and TABLE_NAME=%s",
                   ("alumni", old_table_name,))
    table_column_names_tuples = cursor.fetchall()
    TABLE_COLUMN_NAMES = []

    for dict in table_column_names_tuples:
        y = dict['COLUMN_NAME']
        TABLE_COLUMN_NAMES.append(y)

    try:
        # making query
        query = "RENAME TABLE "+old_table_name+" TO " + new_table_name
        cur = mysql.get_db().cursor()
        cur.execute(query)
        mysql.get_db().commit()

        # table after query execution
        cur = mysql.get_db().cursor()
        cur.execute(f"SELECT * FROM {new_table_name}")
        mysql.get_db().commit()
        table_data_after = cur.fetchall()

        return render_template('tables_before_after.html', table_before=table_data_before, table_after=table_data_after, table_name=new_table_name,
                               table_col_names=TABLE_COLUMN_NAMES, old_table_name=old_table_name, new_table_name=new_table_name)
    except:
        return render_template('errors.html', errorMessage="Rename Error- Re-check your input for New Table Name")


if __name__ == '__main__':
    app.run(debug=True, port=4999)


# dynamic route for rendering updated tables after performing an operation (Insert, Delete, Update or Rename)
# @app.route('/tables/entries/<table_name>', methods =['POST'] )
# def dynamic_table(table_name):
#     if session["logged_in"] == False:
#         return redirect('/')
#     table_name = table_name

#     table_name_string = str(table_name)
#     table_name_string = table_name_string.encode('utf-8').decode('utf-8')
#     table_name_string = str(table_name_string)

#     cur = mysql.get_db().cursor()
#     cur.execute(f"SELECT * FROM {table_name_string}")
#     mysql.get_db().commit()
#     table_data = cur.fetchall()

#     cursor = mysql.get_db().cursor(pymysql.cursors.DictCursor)
#     cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s and TABLE_NAME=%s", ("alumni", table_name_string,))
#     table_column_names_tuples = cursor.fetchall()
#     TABLE_COLUMN_NAMES =[]

#     for dict in table_column_names_tuples:
#         x = dict['COLUMN_NAME']
#         TABLE_COLUMN_NAMES.append(x)

#     cur.close()
#     return render_template('display_entries.html', userDetails=table_data, table_name=table_name_string, table_col_names=TABLE_COLUMN_NAMES, EntriesOrSchema="Entries",
#                             display_edit_buttons="YES",display_edit_fields="NO")


# updating rendered output based on button pressed.

# @app.route('/tables', methods =['POST'])
# def tables_post():
#     x = request.form

#     button_pressed=None
#     table_name = x['tableName']

#     if(x.get('entries')==None):
#         button_pressed='schema'
#     else:
#         button_pressed='entries'

#     table_name_string = str(table_name)
#     table_name_string = table_name_string.encode('utf-8').decode('utf-8')
#     table_name_string = str(table_name_string)


#     #determing rendered output based on button pressed- View Schema or View Entries

#     if(button_pressed=='entries'):

#         cur = mysql.get_db().cursor()
#         try:
#             cur.execute(f"SELECT * FROM {table_name_string}")
#             mysql.get_db().commit()
#             table_data = cur.fetchall()

#             cursor = mysql.get_db().cursor(pymysql.cursors.DictCursor)
#             cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s and TABLE_NAME=%s", ("alumni", table_name_string,))
#             table_column_names_tuples = cursor.fetchall()
#             TABLE_COLUMN_NAMES =[]

#             for dict in table_column_names_tuples:
#                 x = dict['COLUMN_NAME']
#                 TABLE_COLUMN_NAMES.append(x)

#             cur.close()

#             return render_template('display_entries.html', userDetails=table_data, table_name=table_name_string, table_col_names=TABLE_COLUMN_NAMES, EntriesOrSchema="Entries",
#                                 display_edit_buttons="YES",display_edit_fields="NO")

#         except Exception as e:


#             return render_template('errors.html', errorMessage="Table not defined")


#     else:

#         cur = mysql.get_db().cursor()
#         try:
#             cur.execute(f"SHOW COLUMNS FROM {table_name_string}")
#             mysql.get_db().commit()
#             table_data = cur.fetchall()
#             TABLE_COLUMN_NAMES = ["Field","Type","Null","Key","Default","Extra"]
#             cur.close()

#             return render_template('display_entries.html', userDetails=table_data, table_col_names=TABLE_COLUMN_NAMES, table_name=table_name_string, EntriesOrSchema="Schema",
#                                 display_edit_buttons="NO",display_edit_fields="NO")
#         except:
#             return render_template('errors.html', errorMessage="Table not defined")
