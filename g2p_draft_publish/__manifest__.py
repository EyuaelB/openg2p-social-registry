{
    "name": "Draft Publish",
    "version": "17.0.0.0.0",
    "summary": "Draft Publish  Module",
    "category": "tools",
    "depends": ["base", "mail", "g2p_social_registry", "g2p_registry_addl_info", "web"],
    "data": [
        "security/rules.xml",
        "security/ir.model.access.csv",
        "data/enrichment_status.xml",
        "views/configurations.xml",
        "views/draft_imported_records.xml",
        "views/imported_records.xml",
        "wizards/add_followers.xml",
        "wizards/rejection.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "g2p_draft_publish/static/src/**/*.js",
            "g2p_draft_publish/static/src/**/*.css",
            "g2p_draft_publish/static/src/**/*.scss",
            "g2p_draft_publish/static/src/**/*.xml",
        ],
    },
    "author": "OpenG2P",
    "website": "https://openg2p.org",
    "installable": True,
    "application": False,
    "auto_install": False,
    # "images": ["static/description/Banner.gif"],
    "license": "",
}