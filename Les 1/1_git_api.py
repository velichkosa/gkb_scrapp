import json
import requests


def repo_json():
    author_name = 'binance'  # input('Set name repo author:')
    r_repos = requests.get(f'https://api.github.com/users/{author_name}/repos')
    if r_repos.status_code == 200:
        path = author_name + '_rep.json'
        with open(path, 'w') as f:
            json.dump(r_repos.json(), f, indent=2)
        print(f'Repos full name for author {author_name}:')
        for i in r_repos.json():
            print(i['full_name'])
    else:
        print('ERROR STATUS CODE')


if __name__ == "__main__":
    repo_json()
