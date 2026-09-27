#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 21:02:52 2026

@author: JustSwapping
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 20:41:03 2026

@author: JustSwapping
"""

import sqlite3
conn = sqlite3.connect("swaps.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM swaps")
for row in cursor.fetchall():
    print(dict(row))
conn.close()