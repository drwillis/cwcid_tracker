# Add repositories with URLs and emails for where to send the report
repo_dict_data = [
    {
        "type": "Overleaf",
        "auth": "Overleaf",
        "name": "Article Project A",
        "url": "https://git.overleaf.com/aaaaaaaaaaaaaaaaaaaaaaaaa",
        "notify": {
            "TO": ["studentA@university.edu"],
            "CC": ["facultyB@university.edu"],
            "Reply-to": ["facultyB@university.edu"]
        },
    }, {
        "type": "Overleaf",
        "auth": "Overleaf",
        "name": "Article Project B",
        "url": "https://git.overleaf.com/aaaaaaaaaaaaaaaaaaaaaaaaa",
        "notify": {
            "TO": ["studentB@university.edu"],
            "CC": ["facultyB@university.edu"],
            "Reply-to": ["facultyB@university.edu"]
        },
    }, {
        "type": "Github",
        "auth": "GithubPublic",
        "name": "github.com/mylab/code_projectA",
        "url": "https://github.com/mylab/code_projectA",
        "notify": {
            "TO": ["studentA@university.edu"],
            "CC": ["facultyB@university.edu"],
            "Reply-to": ["facultyB@university.edu"]
        },
    }, {
        "type": "Github",
        "auth": "GithubPublic",
        "name": "github.com/mylab/code_projectB",
        "url": "https://github.com/mylab/code_projectB",
        "notify": {
            "TO": ["studentB@university.edu"],
            "CC": ["facultyB@university.edu"],
            "Reply-to": ["facultyB@university.edu"]
        },
    }
]
