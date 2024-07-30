import os
import requests
import subprocess

class GitHubRollback:
    def __init__(self, github_token, repo_owner, repo_name):
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def run_git_command(self, command):
        """Run a git command and return the output."""
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return None
        return result.stdout.strip()

    def get_latest_merged_pr(self):
        """Fetch the latest merged PR on the main branch."""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls"
        params = {
            "state": "closed",
            "base": "main",
            "sort": "updated",
            "direction": "desc"
        }
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            prs = response.json()
            for pr in prs:
                if pr['merged_at'] is not None:
                    return pr['number'], pr['merge_commit_sha']
        else:
            print(f"Failed to fetch PRs: {response.json()}")
        return None, None

    def create_revert_branch(self, merge_commit_hash):
        """Create a new branch and revert the specified commit."""
        revert_branch = f"revert-{merge_commit_hash[:7]}"
        self.run_git_command(['git', 'checkout', 'master'])
        self.run_git_command(['git', 'checkout', '-b', revert_branch])
        self.run_git_command(['git', 'revert', '-m', '1', merge_commit_hash])
        self.run_git_command(['git', 'push', 'origin', revert_branch])
        return revert_branch

    def create_pull_request(self, title, body, head_branch, base_branch='main'):
        """Create a pull request using the GitHub API."""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
        }
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code == 201:
            pr_data = response.json()
            print(f"Pull request created: {pr_data.get('html_url')}")
        else:
            print(f"Failed to create pull request: {response.json()}")

    def revert_latest_merged_pr(self):
        """Revert the latest merged PR and create a new PR for the revert."""
        pr_number, merge_commit_hash = self.get_latest_merged_pr()
        if pr_number and merge_commit_hash:
            print(f"Reverting merge commit from PR #{pr_number}: {merge_commit_hash}")
            revert_branch = self.create_revert_branch(merge_commit_hash)
            title = f"Revert PR #{pr_number}"
            body = f"This reverts the changes from PR #{pr_number}."
            self.create_pull_request(title, body, revert_branch)
        else:
            print("No merged PR found on the main branch.")

if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")
    
    if not github_token or not repo_owner or not repo_name:
        print("Environment variables GITHUB_TOKEN, REPO_OWNER, and REPO_NAME must be set.")
    else:
        rollback = GitHubRollback(github_token, repo_owner, repo_name)
        rollback.revert_latest_merged_pr()
