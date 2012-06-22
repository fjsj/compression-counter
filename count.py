import sys
import requests
from bs4 import BeautifulSoup
from collections import deque, Counter
from pool import ThreadPool
from archive_types import archive_types

import logging
logger = logging.getLogger('compression_counter')
hdlr = logging.FileHandler('compression_counter.log')
hdlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)
error_log = open("error.log", 'w')
sys.stderr = error_log # redirect errors to file
http_log = open("http.log", 'w')

search_urls = []

for i in xrange(1, 10):
    search_urls.append("http://sourceforge.net/directory/language:java/?q=java&sort=popular&page=%s" % i)

project_names = []

for url in search_urls:
    html = requests.get(url, config=dict(max_retries=5, verbose=http_log)).content
    soup = BeautifulSoup(html)

    for a in soup.select(".projects .project_info header a"):
        a_href = a['href']
        project_name = a_href.split("/")[2] # splits /project/ubuntu/ in ['', 'projects', 'ubuntu', '']
        project_names.append(project_name)

logger.info("Will analyse the following projects: " + ", ".join(project_names)) 

def get_extension(s):
    ext2 = s[s.rindex('.'):]
    s_no_ext = s[:s.rindex('.')]
    try:
        ext1 = s_no_ext[s_no_ext.rindex('.'):]
    except ValueError:
        return ext2
    return ext1 + ext2

ext_counter = Counter()

def visit_project_file(url):
    logger.info("Visiting " + url)
    html = requests.get(url, config=dict(max_retries=5, verbose=http_log)).content
    soup = BeautifulSoup(html)

    for a in soup.select("#files_list tr th a.name"):
        file_url = a['href']
        if file_url.endswith('/download'): # is file
            logger.info("Found file " + file_url)
            filename = file_url.split('/')[-2] # splits and gets the word before /download, which is the filename
            try:
                extension = get_extension(filename)
                if extension in archive_types:
                    proj_ext_counter[extension] += 1
            except ValueError: # file without extension
                pass
        else: # is a directory
            file_queue.append("http://sourceforge.net" + file_url)

pool = ThreadPool(16)
for project_name in project_names:
    proj_ext_counter = Counter()
    file_queue = deque(["http://sourceforge.net/projects/%s/files/" % project_name])
    while file_queue:
        url = file_queue.popleft()
        pool.add_task(visit_project_file, url)
        if not file_queue:
            pool.wait_completion()
    try:
        extension, count = proj_ext_counter.most_common(1)[0]
        ext_counter[extension] += 1
    except IndexError: # no known archive files in project
        pass

print ext_counter
logger.info("Result: %s" % ext_counter)
error_log.close()
http_log.close()
