import subprocess
import multiprocessing
import argparse
import os

# quick thrown together script for parallel downloadind with wget. 
# I've made it so this is easily callable froma terminal.

# example run command for a txt file and asking for 2 cores, saving into a chosen folder.
# python wget_pp.py url_test_file.txt -n 2 -o /path/to/output -u myusername -p mypassword


def download(args):
    url, output_dir, user, password = args

    action = url.split("/")[-2]

    directory = os.path.join(output_dir, action)
    os.makedirs(directory, exist_ok=True)

    filename = url.split("/")[-1]

    cmd = (
        f'curl -u "{user}:{password}" '
        f'-o "{directory}/{filename}" '
        f'"{url}" '
        f'-f -s'
    )

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    status = "OK" if result.returncode == 0 else "FAILED"

    if result.returncode != 0:
        print(f"[{status}] {url}")
        print(result.stderr)

    return (url, result.returncode)



def main():

    # this creates command line arguments.
    parser = argparse.ArgumentParser(
        prog="wget files in parallel",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="downloads files in parallel given a txt file of urls and number of cores.",
    )

    positionals = parser.add_argument_group("Positional arguments")
    positionals.add_argument(
        "input",
        help="input url txt file",
        type=str,
    )
    optional = parser.add_argument_group("Optional arguments")
    optional.add_argument(
        "-n",
        "--num-workers",
        help="Number of CPUs to use for parallel downloading urls.",
        dest="n",
        type=int,
        default=1,
        required=False,
    )
    optional.add_argument(
        "-o",
        "--output-dir",
        help="Base directory to save downloaded files into.",
        dest="output_dir",
        type=str,
        default=".",
        required=False,
    )
    optional.add_argument(
        "-u",
        "--username",
        help="Username for downloading files.",
        dest="user",
        type=str,
        required=True,
    )
    optional.add_argument(
        "-p",
        "--password",
        help="Password for downloading files.",
        dest="password",
        type=str,
        required=True,
    )

    args = parser.parse_args()

    return execute(args)


def execute(args):

    # Read URLs from txt file
    with open(args.input) as f:
        urls = [line.strip() for line in f if line.strip()]  # creates list of urls

    print(f"Total URLs: {len(urls)}")

    num_workers = args.n  # number of cores you want to use. command line argument -n

    tasks = [(url, args.output_dir, args.user, args.password) for url in urls]

    with multiprocessing.Pool(processes=num_workers) as pool:
        # spreads urls accross the cores and downloads them. each core is in a loop with a given chunk of urls
        results = pool.map(download, tasks)

    # incase some files fail to run I've added this to recored what files need downloaded still
    failed = [url for url, code in results if code != 0]
    print(f"\nDone. {len(urls) - len(failed)} succeeded, {len(failed)} failed.")

    if failed:
        with open("failed_urls.txt", "w") as f:
            f.write("\n".join(failed))
        print("Failed URLs written to failed_urls.txt")


if __name__ == "__main__":
    main()
