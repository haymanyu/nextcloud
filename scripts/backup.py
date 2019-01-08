#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
import logging
import subprocess
import os
import time

logging.basicConfig(level=logging.INFO, stream=sys.stdout)


class UPLOAD:
    def __init__(self, secret_id, secret_key,
                 bucket_name, region='ap-chengdu'):
        self.Bucket = bucket_name
        self.Secret_id = secret_id
        self.Secret_key = secret_key
        self.region = region
        self.token = None
        self.scheme = 'https'

    def Client(self):
        config = CosConfig(Region=self.region,
                           Secret_id=self.Secret_id,
                           Secret_key=self.Secret_key,
                           Token=self.token,
                           Scheme=self.scheme)

        return CosS3Client(config)

    def Upload(self, key, file):
        client = self.Client()
        # file_name = file.split("/")[-1]
        response = client.upload_file(
            Bucket=self.Bucket,
            LocalFilePath=file,
            Key=key,
            PartSize=10,
            MAXThread=10,
            EnableMD5=False
        )
        return response['ETag']

    def GetTempUrl(self, key, expried=300):
        client = self.Client()
        response = client.get_presigned_download_url(
                Bucket=self.Bucket,
                Key=key,
                Expired=expried
        )
        return response


client = UPLOAD(
    bucket_name='pics-1254407452',
    secret_key='1rszYyFPDeu1Qm3T6bw7JOj2GfyTo3cC',
    secret_id='AKIDo29AFA3PUq296xnTWntreS9pO3iGKHHF',
    region='ap-chengdu'
    )


def runShell(cmd):
    output = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out, err = output.communicate()
    return out.decode().rstrip().lstrip()


def main():
    # 获取 Compose 文件.
    WorkDir = os.path.split(os.path.realpath(__file__))[0]
    ComposeFile = runShell('ls %s/.. | grep docker-compose' % WorkDir)
    ComposePath = WorkDir+'/../'+ComposeFile
    ContainersCMD = """
        docker-compose -f %s ps | awk '{print $1}' \
        | grep -v '\-\-*\-\-' | grep -v 'Name'
        """ % ComposePath

    # 获取 nextcloud 服务对应的容器.
    Containers = runShell(ContainersCMD).split('\n')
    NCContainer = ''
    DBContainer = ''

    for container in Containers:
        ImageCMD = """
            docker inspect -f '{{ .Config.Image}}' %s
        """ % container
        Image = runShell(ImageCMD)
        if Image == 'nextcloud':
            NCContainer = container
        elif Image == 'postgres':
            DBContainer = container
        else:
            pass

    # 获取文件的存储路径
    cmd1 = """
        docker inspect -f '{{ range .Mounts }}
        {{ if eq .Destination "/var/www/html/data"}}
        {{ .Source }}{{ end }}{{ end }}' %s
        """ % NCContainer

    # 获取 nextcloud 的账号.
    cmd2 = """
        docker exec -it -u postgres %s \
        psql -d nextcloud -q -t -c "select uid from accounts;"
        """ % DBContainer

    RootPath = runShell(cmd1)
    Accounts = runShell(cmd2).replace('\r\n ', ',').split(',')
    print(Accounts)
    # 账号校验
    Account = 'admin'
    if Account in Accounts:
        pass
    else:
        raise NameError('Invalid Account')

    Path = RootPath+'/'+Account+'/files'
    Files = []

    # Default TimeControl is today.
    Year = time.gmtime().tm_year
    Month = time.gmtime().tm_mon
    Day = time.gmtime().tm_mday
    TimeControl = time.mktime((Year, Month, Day, 0, 0, 0, 0, 0, 0))

    # 只允许指定时间之后创建或者编辑的文件上传.
    for dirpath, dirnames, filenames in os.walk(Path):
        for file in filenames:
            File = dirpath+'/'+file
            UpdatedAt = max(os.stat(File).st_mtime, os.stat(File).st_mtime)
            if UpdatedAt >= TimeControl:
                Files.append(File)
            else:
                pass

    for File in Files:
        Key = File.replace(RootPath+'/', '')
        Expried = 300
        client.Upload(Key, File)
        URL = client.GetTempUrl(Key, Expried)
        print (URL)


if __name__ == "__main__":
    main()
