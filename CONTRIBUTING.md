# Contributing

Contributions are welcome and are greatly appreciated! Every little bit helps, and credit will always be given, regardless
of how big or small your fix is (typo's included).

## Conventions
Takeoff uses a number of conventions:
- We use [black](https://pypi.org/project/black/) to enforce strict adherence to the [PEP8](https://www.python.org/dev/peps/pep-0008/) code standard.
- We also run [flake8](http://flake8.pycqa.org/en/latest/) to further ensure 
- If you update code in any way, make sure that the documentation is updated to reflect this. The documentation can be found
in the `docs` directory in this repository.
- Use type hints everywhere.
- Names are always Capitalized, in documentation and docstrings


## Issues
If you run into a problem while using Takeoff, please let us know! Also be sure to check the existing issue list, as someone else
may have already reported the issue before you.

## Pull Requests
If you've spotted a typo, bug, any other type of issue, or you'd like to add a new feature, you are very welcome to fix it! Please open a Pull Request and we'll
review your contribution. A few things to keep in mind when opening a PR:
- The CI should pass. This means:
    - All tests should pass
    - The code should pass linting checks
- If you've added any code, be sure to add some tests or update existing tests where necessary
- Please adhere to the PR template. This makes it easier to us to understand what your PR fixes or adds.
- Please use good, descriptive git commit messages, and ensure that commit squashing has been done where appropriate. We want
to keep our git commit history somewhat clean, and adhering to this point will ensure that. [This post](https://chris.beams.io/posts/git-commit/) gives a good description
of what a good commit message should look like.
