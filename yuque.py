# -*- coding:utf-8 -*-
"""
Created Date:
   2025-03-11, 11:45:49
Author:
   luanpan (luanpan@corp.netease.com)

config.json:
{
    "TOKEN": "your token",
    "USER_AGENT": "yuque_export",
    "BASE_URL": "https://customspace.yuque.com/api/v2",
    "DATA_PATH": "yuque_data"
}
"""


import json
import sys
import os
import re
import requests
import yaml
from datetime import datetime

MyPath = os.path.dirname(os.path.abspath(__file__))


class ExportYueQueDoc:
    def __init__(self):
        try:
            self.jsonConfig = json.load(open(os.path.join(MyPath, "config.json"), encoding="utf-8"))
            self.base_url = self.jsonConfig["BASE_URL"]
            self.token = self.jsonConfig["TOKEN"]
            self.headers = {
                "User-Agent": self.jsonConfig["USER_AGENT"],
                "X-Auth-Token": self.jsonConfig["TOKEN"],
            }
            self.data_path = self.jsonConfig["DATA_PATH"]

            self.get_user_info()
        except:
            raise ValueError("config.json 有误")

    def get_user_info(self):
        res_obj = requests.get(url=self.base_url + "/user", headers=self.headers)
        if res_obj.status_code != 200:
            raise ValueError("Token 信息错误")
        user_json = res_obj.json()
        self.login_id = user_json["data"]["login"]
        self.uid = user_json["data"]["id"]
        self.username = user_json["data"]["name"]
        print("=========== 用户信息初始化成功 ==========")

    def get_repos_data(self):
        repos_json = requests.get(self.base_url + "/users/" + self.login_id + "/repos", headers=self.headers).json()
        repos_list = []
        for item in repos_json["data"]:
            rid = item["id"]  # 知识库id
            name = item["name"]  # 知识库名称
            repos_list.append({"rid": rid, "repos_name": name})
        return repos_list

    def save_repos_toc(self):
        repos_list = self.get_repos_data()

        for repos in repos_list:
            article_datas = requests.get(f"{self.base_url}/repos/{repos['rid']}", headers=self.headers).json()

            toc_yaml = article_datas["data"]["toc_yml"]
            toc_data = yaml.safe_load(toc_yaml)
            repos["toc"] = toc_data[1:]
            with open(f"toc/{repos['repos_name']}.json", "w", encoding="utf-8") as fp:
                json.dump(repos, fp, ensure_ascii=False, indent=4)

    def save_repos_articles(self, repos_data):
        rid = repos_data["rid"]
        repos_name = repos_data["repos_name"]
        toc = repos_data["toc"]
        print(f"开始导出知识库：{repos_name}")
        repos_dir = os.path.join(self.data_path, repos_name)
        uuid2Dir = {}
        articles = []
        for t in toc:
            title = t["title"]
            title = re.sub('[\\\/:\*\?"<>\|]', "", title)
            if t["parent_uuid"]:
                parentDir = uuid2Dir[t["parent_uuid"]]
            else:
                parentDir = repos_dir
            t_path = os.path.join(parentDir, title)
            uuid2Dir[t["uuid"]] = t_path
            if t["type"] == "DOC":
                filename = f"{t_path}.md"
                articles.append({"filename": filename, "doc_id": t["doc_id"]})

        for article in articles:
            content = self.get_article_content(article["doc_id"], rid)
            self.save_article(content, article["filename"])

    def get_article_content(self, doc_id, rid):
        per_article_data = requests.get(
            f"{self.base_url}/repos/{rid}/docs/{doc_id}",
            headers=self.headers,
        ).json()
        posts_text = re.sub(r"\\n", "\n", per_article_data["data"]["body"])
        result = re.sub(r'<a name="(.*)"></a>', "", posts_text)
        return result

    def save_article(self, result, filename):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dir_ret = os.path.dirname(filename)
        if not os.path.exists(dir_ret):
            os.makedirs(dir_ret)
        try:
            with open(filename, "a", encoding="utf-8") as fp:
                fp.writelines(result)
                print(f"[{current_time}]  {filename} 导出完成")
        except Exception as e:
            print(e)
            print(f"[{current_time}]  {filename} 导出失败")


def main():
    yq = ExportYueQueDoc()
    yq.save_repos_toc()
    for root, dirs, files in os.walk("toc"):
        for file in files:
            with open(os.path.join(root, file), "r", encoding="utf-8") as fp:
                repos_data = json.load(fp)
                yq.save_repos_articles(repos_data)


if __name__ == "__main__":

    main()
