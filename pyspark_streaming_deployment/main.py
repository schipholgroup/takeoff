from pyspark_streaming_deployment.util import get_tag, get_branch, get_short_hash


def main(func):
    tag = get_tag()
    branch = get_branch()
    git_hash = get_short_hash()

    if tag:
        func(tag, 'PRD')
    elif branch == 'master':
        func('SNAPSHOT', 'ACP')
    else:
        func(git_hash, 'DEV')
