import requests
from pathvalidate import sanitize_filename
import praw
from PyQt5.QtCore import QThread, pyqtSignal
import hashlib
from pathlib import Path
from multiprocessing import Pool
import os


def _calc_hash(existing_file: Path):
    chunk_size = 1024 * 1024
    md5_hash = hashlib.md5()
    with existing_file.open("rb") as file:
        chunk = file.read(chunk_size)
        while chunk:
            md5_hash.update(chunk)
            chunk = file.read(chunk_size)
    file_hash = md5_hash.hexdigest()
    return existing_file, file_hash

class Scrapper(QThread):
    progress_updated = pyqtSignal(int)
    finished_execution = pyqtSignal()  
    
    def __init__(self) -> None:
        super(Scrapper, self).__init__()    
        self.user_agent = 'random-text'
        self.reddit = None
        self.folder_path = None
        self.stop_signal = False

    def login(self, client_id, client_secret, username, password):
        try:
            # Initialize the Reddit API client
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=self.user_agent,
                username=username,
                password=password
            )
            if reddit.user.me():
                self.reddit = reddit
            else:
                self.reddit = False
        except Exception as e:
            self.reddit = False

    def check_subreddit_existance(self, subreddit_name):
        self.subreddit = self.reddit.subreddit(subreddit_name)
        try:
            self.subreddit.title
            return True
        except:
            return False


    def run(self):
        self.progress_updated.emit(0)
        # Calculate hashes for existing files and detect 'ImageId' from EXIF data
        self.master_hash_list, self.master_image_ids_list = self.scan_existing_files(self.folder_path)

        posts = list(self.subreddit.hot(limit=None))
        # Remove duplicates by image_id
        posts = [post for post in posts if post.name not in self.master_image_ids_list]
        
        # Remove posts which are not image types
        posts = [post for post in posts if post.post_hint == 'image']

        if len(posts) == 0:
            self.progress_updated.emit(100)

        print(f'total posts {len(posts)}')
        self.total_downloaded = 0
        counter = 0
        for post in posts:
            if self.stop_signal:
                break
            counter += 1
            resource_url = post.preview['images'][0]['source']['url']
            # print(resource_url)
            response = requests.get(resource_url)
            if response.status_code == 200:
                # Remove duplicated by calculating hash
                resource_hash = hashlib.md5(response.content)
                resource_hash = resource_hash.hexdigest()
                if resource_hash not in self.master_hash_list:
                    # save image
                    clean_title = sanitize_filename(post.title, platform='Windows')

                    with open(os.path.join(self.folder_path, clean_title+f'-{post.name}.jpg'), 'wb') as handler:
                        handler.write(response.content)
                    self.total_downloaded += 1

            self.progress_updated.emit( int(100*counter/len(posts)) )

        self.finished_execution.emit()  


    @staticmethod
    def scan_existing_files(directory) -> dict[str, Path]:
        files = []
        for (dirpath, _dirnames, filenames) in os.walk(directory):
            files.extend([Path(dirpath, file) for file in filenames])
        print(f"Calculating hashes for {len(files)} files")

        pool = Pool(15)
        results = pool.map(_calc_hash, files)
        pool.close()

        hash_list = {res[1]: res[0] for res in results}

        image_ids = []
        for existing_file in files:
            try:
                image_id = str(existing_file).split('-')[-1].split('.')[0]
                if image_id.startswith('t3_'):
                    image_ids.append(image_id)
            except:
                pass
        return hash_list, image_ids
  
