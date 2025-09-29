# sheltertree_project/configuration/username_blacklist.py

"""
This file contains the definitive, centralized list of forbidden usernames
for the ShelterTree platform.
This approach keeps the main settings file clean and makes this list
easy to manage and update.
"""

BLACKLIST = [
    # 1. Staff & Admin Impersonation
    'admin', 'administrator', 'mod', 'moderator', 'staff', 'support', 'help', 'info',
    'sheltertree', 'shelter_tree', 'sheltertreeadmin', 'mysheltertreeadmin', 'myshelteradmin',

    # 2. Generic & Reserved System-Like Names
    'root', 'superuser', 'system', 'config', 'test', 'guest', 'user', 'username',
    'anonymous', 'anon', 'me', 'you', 'all', 'everyone',

    # 3. URL & Route Confusion
    'accounts', 'profile', 'settings', 'legal', 'privacy', 'terms', 'contact', 'about',
    'faq', 'api', 'static', 'media', 'assets', 'images', 'files', 'search', 'explore',
    'properties', 'reviews', 'login', 'logout', 'signup', 'password', 'reset',

    # 4. Commercial & Spam Terms
    'sales', 'marketing', 'jobs', 'careers', 'hiring', 'ads', 'advertise', 'press',
    'business', 'company', 'shop', 'store',

    # 5. Profanity & Abusive Language
    'asshole', 'bitch', 'bullshit', 'cock', 'cunt', 'dick', 'damn', 'fuck', 'hell',
    'piss', 'pussy', 'shit', 'slut', 'whore', 'cum',

    # 6. Hate Speech & Slurs (Example)
    'nazi', 'kkk', 'nigga', 'redneck',
    
    # 7. Common TLDs and Web Terms
    'com', 'net', 'org', 'io', 'app', 'dev', 'www', 'http', 'https',
]