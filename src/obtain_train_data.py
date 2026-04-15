import requests

files = [f"dialogues_{str(i).zfill(3)}.json" for i in range(1, 18)]
base_url = "https://raw.githubusercontent.com/budzianowski/multiwoz/refs/heads/master/data/MultiWOZ_2.2/train/"

for f in files:
    r = requests.get(base_url + f)
    with open(f"data/train/{f}", "wb") as out:
        out.write(r.content)
    print(f"Downloaded {f}")