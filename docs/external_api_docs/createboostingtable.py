# 使用方法：脚本同路径下创建hot.txt的文本文件，里面是热词内容。脚本中填写appid、AK、SK和想要创建的热词表名称，调用即可

# AKSK获取 https://console.volcengine.com/iam/keymanage/
# 结合文档内api说明调用`CreateBoostingTable` 的例子(*其他语言和使用sdk调用的方式请参考火山鉴权源码[说明](https://www.volcengine.com/docs/6369/185600) 一)

import binascii
import datetime
import hashlib
import hmac
import json
import requests
import urllib


def create_boosting_table(
    app_id: int,
    table_name: str,
    file_content: str,
    ak: str,
    sk: str,
) -> requests.Response:
    """
    创建热词表
    
    Args:
        app_id: AppID
        table_name: 热词表名称
        file_content: 热词文件内容
        ak: Access Key
        sk: Secret Key
    """
    
    # API配置
    domain = "open.volcengineapi.com"
    region = "cn-north-1"
    service = "speech_saas_prod"
    
    # 边界字符串
    boundary = "----WebKitFormBoundaryLPAZvyOnASevwDBv"
    content_type = f"multipart/form-data; boundary={boundary}"
    
    # 构建multipart/form-data body
    body_parts = []
    
    # File字段
    body_parts.append(f"--{boundary}")
    body_parts.append('Content-Disposition: form-data; name="File"; filename="test4"')
    body_parts.append("Content-Type: text/plain")
    body_parts.append("")
    body_parts.append(file_content)
    
    # AppID字段
    body_parts.append(f"--{boundary}")
    body_parts.append('Content-Disposition: form-data; name="AppID"')
    body_parts.append("")
    body_parts.append(str(app_id))
    
    # BoostingTableName字段
    body_parts.append(f"--{boundary}")
    body_parts.append('Content-Disposition: form-data; name="BoostingTableName"')
    body_parts.append("")
    body_parts.append(table_name)
    
    # 结束边界
    body_parts.append(f"--{boundary}--")
    body_parts.append("")
    
    # 拼接body
    body = "\r\n".join(body_parts)
    
    # 构建查询参数
    params = {
        "Action": "CreateBoostingTable",
        "Version": "2022-08-30",
    }
    canonical_query_string = get_canonical_query_string(params)
    
    # 构建URL
    url = "https://" + domain + "/?" + canonical_query_string
    
    # 计算payload签名
    payload_sign = get_hmac_encode16(body)
    
    # 构建headers
    headers = get_hashmac_headers(
        domain,
        region,
        service,
        canonical_query_string,
        "POST",
        "/",
        content_type,
        payload_sign,
        ak,
        sk,
    )
    
    # 发送请求
    submit_resp = requests.post(url=url, headers=headers, data=body.encode('utf-8'))
    return submit_resp


def get_canonical_query_string(param_dict):
    target = sorted(param_dict.items(), key=lambda x: x[0], reverse=False)
    canonicalQueryString = urllib.parse.urlencode(target)
    return canonicalQueryString


def get_hmac_encode16(data):
    return binascii.b2a_hex(hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).digest()).decode(
        "ascii"
    )


def get_volc_signature(secret_key, data):
    return hmac.new(secret_key, data.encode("utf-8") if isinstance(data, str) else data, digestmod=hashlib.sha256).digest()


def get_hashmac_headers(
    domain,
    region,
    service,
    canonicalquerystring,
    httprequestmethod,
    canonicaluri,
    contenttype,
    payloadsign,
    ak,
    sk,
):
    utc_time_sencond = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    utc_time_day = datetime.datetime.utcnow().strftime("%Y%m%d")
    credentialScope = utc_time_day + "/" + region + "/" + service + "/request"
    headers = {
        "content-type": contenttype,
        "x-date": utc_time_sencond,
    }
    canonicalHeaders = (
        "content-type:"
        + contenttype
        + "\n"
        + "host:"
        + domain
        + "\n"
        + "x-content-sha256:"
        + "\n"
        + "x-date:{}".format(utc_time_sencond)
        + "\n"
    )
    signedHeaders = "content-type;host;x-content-sha256;x-date"
    canonicalRequest = (
        httprequestmethod
        + "\n"
        + canonicaluri
        + "\n"
        + canonicalquerystring
        + "\n"
        + canonicalHeaders
        + "\n"
        + signedHeaders
        + "\n"
        + payloadsign
    )
    stringToSign = (
        "HMAC-SHA256"
        + "\n"
        + utc_time_sencond
        + "\n"
        + credentialScope
        + "\n"
        + get_hmac_encode16(canonicalRequest)
    )
    signingkey = get_volc_signature(
        get_volc_signature(
            get_volc_signature(
                get_volc_signature(sk.encode("utf-8"), utc_time_day), region
            ),
            service,
        ),
        "request",
    )
    signature = binascii.b2a_hex(get_volc_signature(signingkey, stringToSign)).decode(
        "ascii"
    )
    headers[
        "Authorization"
    ] = "HMAC-SHA256 Credential={}/{}, SignedHeaders={}, Signature={}".format(
        ak, credentialScope, signedHeaders, signature
    )
    return headers


if __name__ == "__main__":
    # 读取热词文件内容
    try:
        with open("hot.txt", "r", encoding="utf-8") as f:
            file_content = f.read().strip()
    except FileNotFoundError:
        print("未找到hot.txt文件，使用示例内容")
        file_content = "秦始皇\n汉武帝\n唐太宗\n宋太祖\n康熙帝"
    
    # 调用创建热词表API
    response = create_boosting_table(
        app_id=123456,
        table_name="YOUR HOTWORDS FILE NAME",
        file_content=file_content,
        ak="",
        sk="",
    )
    
    print("状态码:", response.status_code)
    print("响应内容:", response.text)