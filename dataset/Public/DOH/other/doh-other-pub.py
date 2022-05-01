"""
    代码作用为解析ip是否为DOH服务器
    在443端口上，使用get和post方法对四种URI格式的URL进行请求。
    分别为： dns-query，query。resolve以及空

    输入为ip文件
    输出为五个文件。其中四个为支持四种URI格式的文件，另一个为不支持DOH的ip。
"""

__author__ = "LRX"

import requests
import base64
import dns.message
import dns.rdatatype
import argparse
import multiprocessing as mp
from tqdm import tqdm


def create_query(url, record_type="A", b64=False):
    """
        创建DNS请求，向url查询A记录。使用get查询时，会使用base64编码
    """
    message = dns.message.make_query(url, dns.rdatatype.from_text(record_type)).to_wire()
    if not b64:
        return message
    else:
        return base64.urlsafe_b64encode(message).decode('utf-8').strip("=")


# def decode_b64_answer(data):
#     """
#     将base64格式编码的响应解码为wire message
#     """
#     message = dns.message.from_wire(data)
#     return message


def get_wire(resolver_url, query_name, suffix):
    """
        使用get方法向https://ip/suffix发出DNS请求，参数为base64编码的请求。
        响应成功返回true，否则返回false
    """
    headers = {"accept": "application/dns-message"}
    payload = {"dns": create_query(query_name, b64=True)}
    url = "https://{}/{}".format(resolver_url, suffix)
    try:
        res = requests.get(url, params=payload, headers=headers, stream=True, timeout=10)

        if res.status_code == 200:
            if "Content-Type" in res.headers.keys():
                if res.headers["Content-Type"] == "application/dns-message":
                    return True
    except Exception as e:
        return False


def post_wire(resolver_url, query_name, suffix):
    """
        使用post方法向https://ip/suffix发出DNS请求，参数为wire format格式的dns请求。
        响应成功返回true，否则返回false
    """
    query = create_query(query_name)
    headers = {"accept": "application/dns-message", "content-type": "application/dns-message",
               "content-length": str(len(query))}
    url = "https://{}/{}".format(resolver_url, suffix)
    try:
        res = requests.post(url, data=query, headers=headers, stream=True, timeout=10)

        if res.status_code == 200:
            if "Content-Type" in res.headers.keys():
                if res.headers["Content-Type"] == "application/dns-message":
                    return True
    except Exception as e:
        return False


# def get_json(resolver_url, query_name, suffix):
#     """
#     Not in RFC, but appears to be a common method. Send get with a param name={url}. Response in json
#     :param resolver_url: The resolver to query e.g. 1.1.1.1
#     :param query_name: The query url e.g. example.com
#     :return: a json response from the resolver
#     """
#     headers = {"accept": "application/dns-json"}
#
#     url = "https://{}/{}".format(resolver_url, suffix)
#
#     payload = {"name": query_name}
#
#     try:
#         res = requests.get(url, params=payload, headers=headers, stream=True, timeout=10)
#         return True
#     except Exception as e:
#         return False


def test_resolver(resolver):
    """
        使用get和post方法，向四种URI格式的URL发出请求
        返回一个字典，标识哪一种URI成功响应
    """
    resolver = resolver.rstrip('\n')

    domain = resolver.split(",")[0]
    suffix = resolver.split(",")[1]

    query = "example.com"
    data = {"domain": domain, "flag_res": False, "suffix": suffix}

    post_result = post_wire(domain, query, suffix)
    get_result = get_wire(domain, query, suffix)

    if post_result or get_result:
        data["flag_res"] = True

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Running a series of doh tests")
    parser.add_argument('input', help="Input file containing a list of IPs")
    parser.add_argument('output_dir', help="Output dir to write results to")
    parser.add_argument('-n', '--num_threads', help="Number of threads to execute queries", default=100, type=int)
    args = parser.parse_args()

    in_file = open(args.input)
    targets = in_file.readlines()
    in_file.close()
    if "." not in targets[0]:
        targets = targets[1:]

    threads = min(args.num_threads, len(targets))

    print("Beginning the {} queries using {} threads.".format(len(targets), threads))

    other_path = args.output_dir + "doh_other_suffix.txt"
    no_path = args.output_dir + "no_other_suffix.txt"

    with open(other_path, 'w') as other_file, open(no_path, 'w') as no_file:
        with mp.Pool(processes=threads) as p:
            try:
                for result in tqdm(p.imap_unordered(test_resolver, targets), total=len(targets)):
                    if result["flag_res"]:
                        other_file.write(result["domain"] + "," + result["suffix"] + '\n')
                    else:
                        no_file.write(result["domain"] + "," + result["suffix"] + '\n')

            except KeyboardInterrupt:
                p.terminate()
                p.join()
                print("Exiting early from queries. Current results will still be written")
