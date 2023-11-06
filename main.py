import requests
from bs4 import BeautifulSoup
from konlpy.tag import Okt
from collections import Counter
from urllib.parse import urlparse, urljoin
from requests.exceptions import InvalidSchema, RequestException
import pytagcloud
import webbrowser
from re import match

kkma = Okt() 

f = open('text_data.txt', 'w')

# 웹사이트의 URL을 입력으로 받아서 텍스트를 추출하는 함수
def extract_text_from_url(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    text = ' '.join(soup.stripped_strings)
    return text

# 텍스트에서 명사만 추출하는 함수
def extract_nouns(text):
    okt = Okt()
    nouns = okt.nouns(text)
    return nouns

# 파일에서 제외할 URL 읽는 함수
def read_excluded_urls(file_name):
    with open(file_name, 'r') as file:
        excluded_urls = [line.strip() for line in file]
    return excluded_urls

# 특정 URL을 제외하는 extract_subpage_urls 함수 수정
def extract_subpage_urls(base_url, page_url, excluded_urls_file):
    response = requests.get(page_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    subpage_urls = []

    # 파일에서 제외할 URL 읽기
    excluded_urls = read_excluded_urls(excluded_urls_file)

    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            absolute_url = urljoin(base_url, href)
            # absolute_url이 제외 목록에 있는지 확인하고 없으면 subpage_urls 목록에 추가
            if absolute_url not in excluded_urls:
                subpage_urls.append(absolute_url)
    return subpage_urls

# Function to read excluded words from a text file
def read_excluded_words(file_name):
    with open(file_name, 'r', encoding='utf-8') as file:
        excluded_words = [line.strip() for line in file]
    return excluded_words

# 파일에서 제외할 단어를 읽어와서 해당 단어들을 nouns_count에서 제외하는 코드
def exclude_words_from_count(nouns_count, excluded_words_file):
    excluded_words = read_excluded_words(excluded_words_file)

    for word in excluded_words:
        if word in nouns_count:
            del nouns_count[word]

def read_start_urls(file_name):
    with open(file_name, 'r') as file:
        start_urls = [line.strip() for line in file]
    return start_urls

# 특정 웹 페이지와 그 하위 페이지를 크롤링하는 함수
def crawl_site(excluded_urls_file, base_url, start_urls_file, depth=2):
    visited_urls = set()
    all_nouns = []

    def recursive_crawl(url, current_depth):
        if current_depth > depth:
            return
        if len(visited_urls) >= 300: # 크롤링할 사이트수. 에러나면 숫자 낮추기, 가능하면 많이 하는게 좋음
            return
        if url not in visited_urls:
            visited_urls.add(url)
            print(f"Crawling: {url}")

            try:
                text = extract_text_from_url(url)
                nouns = extract_nouns(text)
                all_nouns.extend(nouns)  # 모든 URL에서 수집된 명사를 all_nouns에 추가

                subpage_urls = extract_subpage_urls(base_url, url, excluded_urls_file)  # Modify to include excluded URLs
                for subpage_url in subpage_urls:
                    recursive_crawl(subpage_url, current_depth + 1)
            except (InvalidSchema, RequestException):
                print(f"올바르지 않은 URL 또는 요청 오류: {url}")

    start_urls = read_start_urls(start_urls_file)

    for start_url in start_urls:
        recursive_crawl(start_url, 1)

    return all_nouns

if __name__ == "__main__":
    base_url = 'https://www.fmkorea.com'  # 대상 웹사이트의 기본 URL로 변경해야 합니다.
    excluded_urls_file = 'excluded_urls.txt'
    excluded_words_file = 'excluded_word.txt'
    start_urls_file = 'start_urls.txt'

    all_nouns = crawl_site(excluded_urls_file, base_url, start_urls_file, depth=2)
    # all_nouns 리스트를 전처리하여 불필요한 문자열과 빈 문자열을 제거
    all_nouns = [noun for noun in all_nouns if len(noun) > 1]

    # 빈 문자열 제거    
    all_nouns = [noun for noun in all_nouns if noun]
    
    ex_nouns = [] # 단어 저장

    for sent in all_nouns : # doc -> sentence
        for noun in kkma.nouns(sent) : # sentence -> noun
            ex_nouns.append(noun)

    nouns_count = {} # 빈 set

    for noun in ex_nouns :
        # 2음절 이상, 숫자 제외
        if len(str(noun)) > 1 and not(match('^[0-9]', noun)) :
            nouns_count[noun] = nouns_count.get(noun, 0) + 1

    # nouns_count에서 제외할 단어를 읽어옴
    exclude_words_from_count(nouns_count, excluded_words_file)

    counter = Counter(nouns_count)
    most_common = counter.most_common(n=200) #n=원하는 데이터 출력수. 현재는 상위 200개의 데이터를 뽑음

    print("전체 페이지에서 가장 많이 나온 단어:")
    for word, count in most_common:
        print(f"{word}: {count}")
        f.write(word + ': ' + str(count) + '\n')

    f.close()

    # pytagcloud.make_tags 함수 호출
    word_count_list = pytagcloud.make_tags(most_common, maxsize=100.0) # maxsize 조정하면 글자 최대 크기 바뀜

    pytagcloud.create_tag_image(word_count_list, 'wordcloud.jpg', size=(900, 600), fontname='korean', rectangular=False) # size=(가로픽셀, 세로픽셀)
    webbrowser.open('wordcloud.jpg') 