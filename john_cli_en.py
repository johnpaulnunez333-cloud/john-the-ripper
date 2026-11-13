import hashlib
import time
import sys
import os
import itertools
import multiprocessing
from cfonts import render
from colorama import init, Fore, Style

init(autoreset=True)

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    output = render('JOHN THE|RIPPER', colors=['red', 'yellow'], align='left', font='block')
    print(output)
    print(f"{Fore.CYAN}    ============================================================")
    print(f"{Fore.CYAN}    |  SCROLLING MODE  |  MAX POWER  |  RULES  |  BRUTEFORCE  |")
    print(f"{Fore.CYAN}    ============================================================\n")

HASH_ALGOS = ['md5', 'sha1', 'sha256', 'sha512']

def get_hash_type(hash_str):
    h = hash_str.strip().lower()
    if len(h) == 32:
        return 'md5'
    if len(h) == 40:
        return 'sha1'
    if len(h) == 64:
        return 'sha256'
    if len(h) == 128:
        return 'sha512'
    if h.startswith('$6$'):
        return 'sha512crypt'
    if h.startswith('$5$'):
        return 'sha256crypt'
    if h.startswith('$1$'):
        return 'md5crypt'
    if h.startswith('$apr1$'):
        return 'apr1'
    return 'ntlm'

def verify(pwd, target, algo):
    algo = algo.lower()
    if algo == 'md5':
        return hashlib.md5(pwd.encode()).hexdigest() == target
    if algo == 'sha1':
        return hashlib.sha1(pwd.encode()).hexdigest() == target
    if algo == 'sha256':
        return hashlib.sha256(pwd.encode()).hexdigest() == target
    if algo == 'sha512':
        return hashlib.sha512(pwd.encode()).hexdigest() == target
    if algo == 'ntlm':
        try:
            return hashlib.new('md4', pwd.encode('utf-16le')).hexdigest() == target
        except Exception:
            return False
    if algo in ('sha512crypt', 'sha256crypt', 'md5crypt', 'apr1'):
        return crypt_check(pwd, target, algo)
    return False

def crypt_check(pwd, target, algo):
    try:
        import crypt as py_crypt
        result = py_crypt.crypt(pwd, target)
        return result is not None and result == target
    except Exception:
        return False

LEET_MAP = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
SUFFIXES = ['1', '12', '123', '1234', '12345', '123456', '!', '!!', '?!',
            '@', '#', '01', '69', '007', '007!', '0', '666', '77', '99',
            '2020', '2021', '2022', '2023', '2024', '2025', '!@#', '!@#$',
            '21', '01!', '2', '3', '4', '5', '6', '7', '8', '9', '0']
YEARS = [str(y) for y in range(1970, 2027)]
PREFIXES = ['1', '!', '@', '#', '123', 'the', 'The', 'THE']

def mangle_word(word):
    variants = set()
    w = word.strip()
    if not w:
        return variants
    base_forms = [w, w.lower(), w.upper(), w.capitalize()]
    for base in base_forms:
        variants.add(base)
        for s in SUFFIXES:
            variants.add(base + s)
        for y in YEARS:
            variants.add(base + y)
        for p in PREFIXES:
            variants.add(p + base)
        rev = base[::-1]
        variants.add(rev)
        variants.add(rev + '1')
        doubled = base + base
        variants.add(doubled)
        leet_full = ''.join(LEET_MAP.get(c, c) for c in base)
        variants.add(leet_full)
        variants.add(leet_full + '1')
        variants.add(leet_full + '!')
        for i in range(len(base)):
            if base[i].isalpha():
                leet_one = base[:i] + LEET_MAP.get(base[i].lower(), base[i]) + base[i+1:]
                variants.add(leet_one)
                variants.add(leet_one + '1')
                variants.add(leet_one + '!')
    return variants

def brute_force(target, algo, charset, max_len, result_q):
    for length in range(1, max_len + 1):
        for combo in itertools.product(charset, repeat=length):
            pwd = ''.join(combo)
            if verify(pwd, target, algo):
                result_q.put(pwd)
                return

_shared = {}

def _init_worker(target_hash, algo, mangle):
    _shared['target'] = target_hash
    _shared['algo'] = algo
    _shared['mangle'] = mangle

def worker_task(chunk):
    target = _shared['target']
    algo = _shared['algo']
    mangle = _shared['mangle']
    for password in chunk:
        pwd = password.strip()
        if not pwd:
            continue
        candidates = mangle_word(pwd) if mangle else {pwd}
        for c in candidates:
            if verify(c, target, algo):
                return c
    return None

def pick_wordlist():
    print(f"{Fore.CYAN}[?] Wordlist Path (ENTER = auto-find rockyou):")
    path = input(f"{Fore.YELLOW}>> {Style.RESET_ALL}").strip()
    if not path:
        candidates = [
            os.path.expanduser('~/wordlists/rockyou.txt'),
            '/usr/share/wordlists/rockyou.txt',
            '/data/data/com.termux/files/home/wordlists/rockyou.txt',
            os.path.expanduser('~/rockyou.txt'),
            os.path.expanduser('~/Downloads/rockyou.txt'),
        ]
        for c in candidates:
            if os.path.exists(c):
                print(f"{Fore.GREEN}[+] Found wordlist: {c}")
                return c
        print(f"{Fore.RED}[!!] No wordlist found. Download rockyou:")
        print(f"{Fore.YELLOW}    mkdir -p ~/wordlists")
        print(f"{Fore.YELLOW}    wget -O ~/wordlists/rockyou.txt https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt")
        return None
    if not os.path.exists(path):
        print(f"{Fore.RED}[!!] File not found: {path}")
        return None
    return path

def start_cracking():
    print_banner()
    target_hash = input(f"{Fore.YELLOW}[?] Enter Target Hash: ").strip().lower()
    if not target_hash:
        return

    algo = get_hash_type(target_hash)
    print(f"{Fore.CYAN}[!] Detected Algorithm: {algo.upper()}")

    if algo in ('sha512crypt', 'sha256crypt', 'md5crypt', 'apr1'):
        print(f"{Fore.YELLOW}[!] Salted hash detected - crypt module will be used")

    mode = input(f"{Fore.YELLOW}[?] Mode: [1] Wordlist+Rules  [2] Pure Bruteforce: ").strip()
    start_time = time.time()
    found_password = None

    if mode == '2':
        charset = input(f"{Fore.YELLOW}[?] Charset (ENTER = full): ").strip()
        if not charset:
            charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%'
        max_len = input(f"{Fore.YELLOW}[?] Max Length (ENTER = 6): ").strip()
        max_len = int(max_len) if max_len.isdigit() else 6
        if max_len > 7:
            print(f"{Fore.YELLOW}[!] WARNING: length {max_len} will take very long on phone CPU")
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}[!!!] BRUTEFORCE MODE ENGAGED...")
        result_q = multiprocessing.Queue()
        p = multiprocessing.Process(target=brute_force,
                                    args=(target_hash, algo, charset, max_len, result_q))
        p.start()
        try:
            found_password = result_q.get()
        except Exception:
            found_password = None
        p.terminate()
    else:
        wordlist_path = pick_wordlist()
        if not wordlist_path:
            return
        mangle_choice = input(f"{Fore.YELLOW}[?] Apply Rules (case/digits/leet/years)? y/n: ").strip().lower()
        mangle = mangle_choice == 'y'

        print(f"\n{Fore.YELLOW}{Style.BRIGHT}[!!!] BRUTEFORCE ATTACK PERFORMING...")
        time.sleep(1)

        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            passwords = f.readlines()

        cpu_count = multiprocessing.cpu_count()
        chunk_size = max(1, len(passwords) // (cpu_count * 4))
        chunks = [passwords[i:i + chunk_size] for i in range(0, len(passwords), chunk_size)]

        print(f"{Fore.CYAN}[!] Loading {len(passwords)} words x rules expansion on {cpu_count} cores\n")

        with multiprocessing.Pool(processes=cpu_count,
                                  initializer=_init_worker,
                                  initargs=(target_hash, algo, mangle)) as pool:
            results = [pool.apply_async(worker_task, (c,)) for c in chunks]
            try:
                total = len(results)
                done = 0
                while done < total:
                    ready = [r for r in results if r.ready()]
                    done = len(ready)
                    for r in ready:
                        res = r.get()
                        if res:
                            found_password = res
                            break
                    if found_password:
                        pool.terminate()
                        break
                    elapsed = time.time() - start_time
                    sys.stdout.write(f"\r{Fore.MAGENTA}[Status] {done}/{total} chunks done | {elapsed:.1f}s   ")
                    sys.stdout.flush()
                    time.sleep(0.05)
            except KeyboardInterrupt:
                pool.terminate()
                return

    if found_password:
        print("\n" + Fore.GREEN + Style.BRIGHT + "█" * 70)
        print(f"{Fore.WHITE} SUCCESS! PASSWORD IDENTIFIED: {Fore.YELLOW}{found_password}")
        print(f"{Fore.WHITE} ALGORITHM USED             : {Fore.CYAN}{algo.upper()}")
        print(f"{Fore.WHITE} TIME ELAPSED               : {time.time() - start_time:.2f}s")
        print(Fore.GREEN + Style.BRIGHT + "█" * 70)
    else:
        print("\n" + Fore.RED + Style.BRIGHT + "X" * 70)
        print(f"{Fore.WHITE} SCAN COMPLETE. NO MATCH FOUND.")
        print(f"{Fore.WHITE} ALGORITHM TESTED: {Fore.CYAN}{algo.upper()}")
        print(f"{Fore.WHITE} TIPS: [1] Use rockyou.txt   [2] Enable Rules (y)")
        print(f"{Fore.WHITE}       [3] Check hash format - salted ($6$) needs crypt")
        print(Fore.RED + Style.BRIGHT + "X" * 70)

if __name__ == "__main__":
    try:
        start_cracking()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Interrupted by user.{Style.RESET_ALL}\n")