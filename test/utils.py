import os
import  stat
from git import Repo


def cloneFrom(repo_url, repo_path, checkout=None, paths=None):
    """Helper function to clone a git repository.

    Args:
        repo_url (str): URL of the git repository.
        repo_path (str): Path where the repository should be cloned.
        checkout (str): Branch or Tag to checkout (default None).
        paths (array): List of directories to check out (default None).

    Returns:
        git.Repo: Instance of git.Repo on success else None.
    """
    repo = None

    if repo_path and repo_url is not None:
        try:
            repo = Repo.init(repo_path, bare=False)
            config = repo.config_writer()
            config.set_value('core', 'sparsecheckout', True)
            config.release()
            origin = repo.create_remote('origin', repo_url)

            if paths is not None:
                with open(os.path.join(repo_path, ".git/info/sparse-checkout"), "w+") as sparse_checkout:
                    # Add required pathsto checkout.
                    for path in paths:
                        sparse_checkout.write(path + "\n")

            origin.fetch()

            if checkout is not None:
                repo.git.checkout(checkout)

        except Exception as ex:
            repo = None
            print("Error: Exception in cloneFrom()")
            print("Error: repo_path: {0}, url: {1}".format(repo_path, repo_url))
            print("Error: Exception type: {0}, message: {1}".format(ex.__class__.__name__, str(ex)))

    return repo


def onerror(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    if not os.access(path, os.W_OK):
        # Is the error an access error ?
        os.chmod(path, stat.S_IWUSR)
        func(path)
