Pack with the following command

[Windows]

``
pyinstaller --onefile --add-data "scheduler_app/templates;templates" --add-data "scheduler_app/static;static" --add-data "scheduler_app/personnel.csv;." scheduler_app/app.py
``


[Mac]


``
pyinstaller --onefile --add-data "scheduler_app/templates:templates" --add-data "scheduler_app/static:static" --add-data "scheduler_app/personnel.csv:." scheduler_app/app.py
``