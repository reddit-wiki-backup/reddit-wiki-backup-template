import configparser
import os

import praw

_WIKI_CONFIG_PAGES = ('config/', 'automoderator/')


class Filepath:
    TASK_CONFIG = 'subreddits.ini'
    BACKUP_DIR = 'backup'


class TaskConfigOption:
    INCLUDE_CONFIG_PAGES = 'include_config_pages'
    INCLUDE_ONLY_PAGES = 'include_only_pages'
    EXCLUDE_PAGES = 'exclude_pages'


class RedditWikiBackup:
    def __init__(self) -> None:
        self._reddit = None
        self._config = None

    def run_backup(self) -> None:
        self._read_config()
        self._create_reddit_instance()
        self._download_subreddit_wikis()
        return

    def _download_subreddit_wikis(self) -> None:
        subreddit_names = list(self._config.keys())
        subreddit_names.remove(self._config.default_section)
        [self._download_one_subreddit_wiki(subreddit_name) for subreddit_name in subreddit_names]
        return

    def _read_config(self) -> None:
        self._config = configparser.ConfigParser()
        self._config.read(Filepath.TASK_CONFIG)
        return

    def _create_reddit_instance(self) -> None:
        if self._reddit:
            return

        username = os.environ['USERNAME']
        self._reddit = praw.Reddit(
            client_id=os.environ['CLIENT_ID'],
            client_secret=os.environ['CLIENT_SECRET'],
            password=os.environ['PASSWORD'],
            user_agent=f'Backup subreddit wiki(s) on behalf of u/{username}',
            username=username,
        )
        return

    def _download_one_subreddit_wiki(self, subreddit_name: str) -> None:
        subreddit = self._reddit.subreddit(subreddit_name)
        subreddit_wiki = subreddit.wiki
        subreddit_backup_dir = os.path.join(Filepath.BACKUP_DIR, subreddit.display_name)

        try:
            os.mkdir(Filepath.BACKUP_DIR)
        except FileExistsError:
            pass

        try:
            os.mkdir(subreddit_backup_dir)
        except FileExistsError:
            pass

        for page_name in self._get_page_names(subreddit_name):
            filepath = os.path.join(subreddit_backup_dir, page_name.replace('/', '.'))
            page = subreddit_wiki[page_name]
            page_content = dict(md=page.content_md, html=page.content_html)
            for ext, content in page_content.items():
                with open('.'.join((filepath, ext)), 'w', encoding='utf8') as f:
                    f.write(content)

        return

    def _get_page_names(self, subreddit_name: str) -> set:
        subreddit_section = self._config[subreddit_name]
        page_names = set(self._reddit.get(f'/r/{subreddit_name}/wiki/pages/')['data'])

        if not subreddit_section.getboolean(TaskConfigOption.INCLUDE_CONFIG_PAGES):
            page_names = set(filter(lambda x: not x.startswith(_WIKI_CONFIG_PAGES), page_names))

        if pages_to_include := subreddit_section.get(TaskConfigOption.INCLUDE_ONLY_PAGES):
            page_names = set(pages_to_include.split()).intersection(page_names)

        if pages_to_exclude := subreddit_section.get(TaskConfigOption.EXCLUDE_PAGES):
            page_names = page_names.difference(set(pages_to_exclude.split()))

        return page_names


def main() -> None:
    backupper = RedditWikiBackup()
    backupper.run_backup()
    return


if __name__ == '__main__':
    main()
