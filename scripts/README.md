# Commandline scripts for milestones

Create a milestone

    # GitHub CLI api
    # https://cli.github.com/manual/gh_api

    gh api \
      --method POST \
      -H "Accept: application/vnd.github.v3+json" \
      /repos/dealii-X/dealii-X/milestones \
      -f title='Demo'
    -f state='open'
    -f description='Dumb milestone for demo purpose'
    -f due_on='2025-02-28T23:39:01Z'
  
Take a look with web brower
firefox <https://github.com/dealii-X/dealii-X/milestones>
List milestones

    # <https://cli.github.com/manual/gh_api>

    gh api \
      -H "Accept: application/vnd.github.v3+json" \
      /repos/dealii-X/dealii-X/milestones

List and format milestones

    gh api \
      -H "Accept: application/vnd.github.v3+json" \
      /repos/dealii-X/dealii-X/milestones \
      | jq -r '.[] | [.id, .number, .title] | @tsv'

Get a milestone

    # GitHub CLI api

    # <https://cli.github.com/manual/gh_api>

    gh api \
      -H "Accept: application/vnd.github.v3+json" \
      /repos/dealii-X/dealii-X/milestones/1
    Get a formated output of milestones
    gh api \
      -H "Accept: application/vnd.github.v3+json" \
      /repos/dealii-X/dealii-X/milestones/1 \
      | jq -r '. | [.title, .description, .html_url, .creator.login] | @tsv'

Look at the milestone with web browser
firefox <https://github.com/dealii-X/dealii-X/milestone/1>
Create issue within the milestone

    gh issue create --milestone "Demo" --title "hello from cli" \
        --repo dealii-X/dealii-X\
        --body "Body bidon from cli"

View issue

    gh issue view 1 --repo dealii-X/dealii-X

    # Then with the web browser

    gh issue view 1 --repo dealii-X/dealii-X --web

List issues of the milestone

    gh issue list --milestone "Demo" --repo dealii-X/dealii-X

    # Then from the web browser

    firefox <https://github.com/dealii-X/dealii-X/milestone/1>

Close the issue

    gh issue close 1 --comment "That was fast"  \
        --repo dealii-X/dealii-X
    List (closed) issues of the milestone
    gh issue list --milestone Demo --state closed \
        --repo dealii-X/dealii-X

List issues with a web browser

    gh issue list --milestone Demo --state closed \
        --repo dealii-X/dealii-X  --web

Close the milestone

    # GitHub CLI api

    # <https://cli.github.com/manual/gh_api>

    gh api --method PATCH -H "Accept: application/vnd.github.v3+json" \
        /repos/dealii-X/dealii-X/milestones/1 \
        -f title='v1.0' -f state='closed' \
        -f description='End of demo' \
        -f due_on='2022-12-25T23:39:01Z'

Check the closed milestone
    gh api \
      -H "Accept: application/vnd.github.v3+json" \
      /repos/dealii-X/dealii-X/milestones/1 \
      | jq -r '. | [.title, .state] | @tsv'

Take a look at the milestone with the web browser

  firefox <https://github.com/dealii-X/dealii-X/milestone/1>

Delete milestone

    # GitHub CLI api

    # <https://cli.github.com/manual/gh_api>

    gh api \
      --method DELETE \
      -H "Accept: application/vnd.github.v3+json" \
      /repos/dealii-X/dealii-X/milestones/1
    Check milestone has been deleted
    gh api \
      -H "Accept: application/vnd.github.v3+json" \
      /repos/dealii-X/dealii-X/milestones/1

    # Then with web browser

    firefox <https://github.com/dealii-X/dealii-X/milestone/1>

Generate deliverables from CSV

    python3 deliverables.py

Generate milestones from CSV

    python3 milestones.py

Generate labels from CSV

    python3 labels.py
