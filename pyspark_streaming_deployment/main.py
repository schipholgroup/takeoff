from pyspark_streaming_deployment.util import get_tag, get_branch


def main(func):
    tag = get_tag()
    branch = get_branch()

    if tag:
        func(tag, 'PRD')
    else:
        if branch == 'master':
            func('SNAPSHOT', 'DEV')
        else:
            print(f'''Not a release (tag not available),
            nor master branch (branch = "{branch}". Not deploying''')
