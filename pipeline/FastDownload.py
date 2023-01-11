# SuperFastPython.com
# download document files concurrently and save the files locally concurrently
from os import makedirs
from os.path import basename
from os.path import join
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

 
# download a url and return the raw data, or None on error
def download_url(url):
    try:
        # open a connection to the server
        with urlopen(url, timeout=3) as connection:
            # read the contents of the html doc
            return (connection.read(), url)
    except:
        # bad url, socket timeout, http forbidden, etc.
        return (None, url)
 
# save data to a local file
def save_file(url, data, path):
    # get the name of the file from the url
    filename = basename(url)
    # construct a local path for saving the file
    outpath = join(path, filename)
    # save to file
    with open(outpath, 'wb') as file:
        file.write(data)
    return outpath
 
# download a list of URLs to local files
def download_docs(urls, path):
    # create the local directory, if needed
    makedirs(path, exist_ok=True)
    # create the thread pool
    n_threads = len(urls)
    with ThreadPoolExecutor(n_threads) as executor:
        # download each url and save as a local file
        futures = [executor.submit(download_url, url) for url in urls]
        # process each result as it is available
        for future in as_completed(futures):
            # get the downloaded url data
            data, url = future.result()
            # check for no data
            if data is None:
                print(f'>Error downloading {url}')
                continue
            # save the data to a local file
            outpath = save_file(url, data, path)
            # report progress
            print(f'>Saved {url} to {outpath}')
 
# python concurrency API docs
URLS = ['https://docs.python.org/3/library/concurrency.html',
        'https://docs.python.org/3/library/concurrent.html',
        'https://docs.python.org/3/library/concurrent.futures.html',
        'https://docs.python.org/3/library/threading.html',
        'https://docs.python.org/3/library/multiprocessing.html',
        'https://docs.python.org/3/library/multiprocessing.shared_memory.html',
        'https://docs.python.org/3/library/subprocess.html',
        'https://docs.python.org/3/library/queue.html',
        'https://docs.python.org/3/library/sched.html',
        'https://docs.python.org/3/library/contextvars.html']
# local path for saving the files
PATH = 'docs'
# download all docs
download_docs(URLS, PATH)
