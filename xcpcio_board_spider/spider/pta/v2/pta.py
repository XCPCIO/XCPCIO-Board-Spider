from itertools import islice
from typing import Optional, Dict, List
import logging

import asyncio
import aiohttp

from xcpcio_board_spider import (
    Contest,
    Submission,
    Submissions,
    Team,
    Teams,
    constants,
    utils,
    Color,
)

logger = logging.getLogger(__name__)


class PTA:
    kTimeOut = 10
    kRetryTimes = 5
    kAcScore = 300

    def __init__(self, contest: Contest, contest_id: str):
        self._contest = contest
        self._contest_id = contest_id
        self._teams = Teams()
        self._runs = Submissions()
        self._team_ids = set()
        self._problem_ids = {}

    async def _fetch_rank_by_uri(self, path: str) -> Optional[Dict]:
        url = f'https://pintia.cn/api/competitions/{self._contest_id}/{path}'

        headers = {
            'accept': 'application/json;charset=UTF-8',
            'accept-language': 'zh-CN',
            'content-type': 'application/json;charset=UTF-8',
            'priority': 'u=1, i',
            'referer': f'https://pintia.cn/rankings/{self._contest_id}',
            'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=self.kTimeOut) as resp:
                if resp.status != 200:
                    raise Exception(
                        f"Failed to fetch {url}, status: {resp.status}")
                return await resp.json()

    async def _fetch_rank(self):
        return await self._fetch_rank_by_uri("xcpc-rankings")

    async def _fetch_groups(self):
        return await self._fetch_rank_by_uri("groups")

    async def _fetch_team_submissions(self, team_id: str):
        return await self._fetch_rank_by_uri(f"xcpc-rankings-team-submissions?team_fid={team_id}")

    def _parse_groups(self, data: Dict):
        group = {}
        for group in data["groups"]:
            name = group['name']
            fid = group['fid']
            group[fid] = name
        self._contest.group = group

    def _parse_contest(self, data: Dict):
        competitionBasicInfo = data['competitionBasicInfo']
        contest = self._contest
        contest.start_time = utils.get_timestamp_from_iso8601(
            competitionBasicInfo['startAt'])
        contest.end_time = utils.get_timestamp_from_iso8601(
            competitionBasicInfo['endAt'])

        xcpcRankings: Dict = data['xcpcRankings']
        problemInfoByProblemSetProblemId: Dict = xcpcRankings[
            'problemInfoByProblemSetProblemId']
        contest.problem_id = []
        contest.balloon_color = []
        problem_ids: Dict = {}
        for p_id, p in problemInfoByProblemSetProblemId.items():
            label = p["label"]
            balloon_rgb = p["balloonRgb"]
            contest.problem_id.append(label)
            contest.append_balloon_color(
                Color(background_color=balloon_rgb, color="#000"))
            problem_ids[p_id] = ord(label) - ord('A')
        contest.problem_quantity = len(contest.problem_id)
        self._problem_ids = problem_ids

    def _parse_teams(self, data: Dict):
        xcpcRankings: Dict = data['xcpcRankings']
        rankings: List[Dict] = xcpcRankings['rankings']

        teams = Teams()
        team_ids = set()
        for r in rankings:
            team_id = str(r['teamFid'])
            team_info: Dict = r['teamInfo']
            team_name = str(team_info['teamName'])
            members = team_info['memberNames']
            school_name = str(team_info['schoolName'])
            excluded = bool(team_info['excluded'])
            girlMajor = bool(team_info['girlMajor'])
            group_fids = team_info['groupFids']

            if excluded:
                continue

            team = Team()
            team.team_id = team_id
            team.name = team_name
            team.organization = school_name
            team.members = members
            team.group = group_fids
            team.girl = girlMajor
            teams[team_id] = team
            team_ids.add(team_id)

        self._teams = teams
        self._team_ids = team_ids

    def _make_fake_runs(self, data: Dict):
        xcpcRankings: Dict = data['xcpcRankings']
        rankings: List[Dict] = xcpcRankings['rankings']

        runs = Submissions()
        for r in rankings:
            team_id = str(r['teamInfo']['teamFid'])
            for p_id, status in r['problemSubmissionDetailsByProblemSetProblemId'].items():
                score = status["status"]
                validSubmitCount = status["validSubmitCount"]
                acceptTime = status["acceptTime"]
                submitCountSnapshot = status["submitCountSnapshot"]
                # TODO(Dup4): make fake runs

        self._runs = runs

    def _parse_status(self, status: str):
        if status == "ACCEPTED":
            return constants.RESULT_ACCEPTED
        if status == "WRONG_ANSWER":
            return constants.RESULT_WRONG_ANSWER
        return constants.RESULT_UNKNOWN

    def _parse_team_runs(self, data: Dict, team_id: str) -> Submissions:
        runs = Submissions()
        submissions = data["submissions"]
        for submission in submissions:
            run = Submission()
            status = self._parse_status(submission["status"])
            problem_id = self._problem_ids[submission["problemSetProblemId"]]
            timestamp = utils.get_timestamp_from_iso8601(
                submission["submitAt"])
            submission_id = submission["submissionId"]
            run.team_id = team_id
            run.status = status
            run.problem_id = problem_id
            run.timestamp = timestamp
            run.submission_id = submission_id
            runs.append(run)
        return runs

    async def _fetch_and_parse_team_runs(self, team_id: str) -> Submissions:
        for i in range(self.kRetryTimes):
            try:
                if i > 0:
                    logger.warning(
                        f"Retry fetch and parse team runs[{i}]: {team_id}")
                data = await self._fetch_team_submissions(team_id)
                return self._parse_team_runs(data, team_id)
            except Exception as e:
                raise e

    async def _process_team_runs_batch(self, team_batch):
        tasks = [self._fetch_and_parse_team_runs(
            team.team_id) for team in team_batch]
        return await asyncio.gather(*tasks)

    async def _parse(self, fetch_runs: bool):
        groups = await self._fetch_groups()
        self._parse_groups(groups)

        rank = await self._fetch_rank()
        self._parse_contest(rank)
        self._parse_teams(rank)

        if not fetch_runs:
            self._make_fake_runs(rank)
            return

        all_runs = Submissions()
        batch_size = 100
        teams = list(self._teams.values())
        for i in range(0, len(teams), batch_size):
            if i > 0:
                await asyncio.sleep(1)
            team_batch = list(islice(teams, i, i + batch_size))
            team_runs_batch = await self._process_team_runs_batch(team_batch)
            for team_run in team_runs_batch:
                all_runs.extend(team_run)
            logger.info(f"Processed {i + len(team_batch)} teams")
        all_runs.sort(key=lambda x: x.timestamp)
        self._runs = all_runs

    def run(self, fetch_runs: bool = False):
        asyncio.run(self._parse, fetch_runs)
