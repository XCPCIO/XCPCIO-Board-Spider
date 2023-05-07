import typing
import json

from .type import *


class Contest:
    def __init__(self,
                 contest_name: str = "",
                 start_time: int = 0,
                 end_time: int = 0,
                 frozen_time: int = 0,
                 penalty: int = 0,
                 problem_quantity: int = 0,
                 problem_id: typing.List[str] = [],
                 group: typing.Any = None,
                 organization: str = "",
                 status_time_display: typing.Any = None,
                 medal: typing.Any = {},
                 balloon_color: typing.List[Color] = [],
                 logo: Image = None):
        self.contest_name = contest_name
        self.start_time = start_time
        self.end_time = end_time
        self.frozen_time = frozen_time
        self.penalty = penalty
        self.problem_quantity = problem_quantity
        self.problem_id = problem_id
        self.group = group
        self.organization = organization
        self.status_time_display = status_time_display
        self.medal = medal
        self.balloon_color = [Color(**item) for item in balloon_color]

        if logo is not None:
            self.logo = Image(**logo)
        else:
            self.logo = None

    def fill_problem_id(self):
        self.problem_id = [chr(ord('A') + i)
                           for i in range(self.problem_quantity)]

        return self

    def fill_balloon_color(self):
        default_balloon_color_list = [
            Color(background_color='rgba(189, 14, 14, 0.7)', color='#fff'),
            Color(background_color='rgba(255, 144, 228, 0.7)', color='#fff'),
            Color(background_color='rgba(255, 255, 255, 0.7)', color='#000'),
            Color(background_color='rgba(38, 185, 60, 0.7)', color='#fff'),
            Color(background_color='rgba(239, 217, 9, 0.7)', color='#000'),
            Color(background_color='rgba(243, 88, 20, 0.7)', color='#fff'),
            Color(background_color='rgba(12, 76, 138, 0.7)', color='#fff'),
            Color(background_color='rgba(156, 155, 155, 0.7)', color='#fff'),
            Color(background_color='rgba(4, 154, 115, 0.7)', color='#fff'),
            Color(background_color='rgba(159, 19, 236, 0.7)', color='#fff'),
            Color(background_color='rgba(42, 197, 202, 0.7)', color='#fff'),
            Color(background_color='rgba(142, 56, 54, 0.7)', color='#fff'),
            Color(background_color='rgba(0, 0, 0, 0.7)', color='#fff'),
        ]

        self.balloon_color = default_balloon_color_list[:self.problem_quantity]

        return self

    @property
    def __dict__(self):
        obj = {}

        obj["contest_name"] = self.contest_name
        obj["start_time"] = self.start_time
        obj["end_time"] = self.end_time
        obj["frozen_time"] = self.frozen_time
        obj["penalty"] = self.penalty
        obj["problem_quantity"] = self.problem_quantity
        obj["problem_id"] = self.problem_id
        obj["group"] = self.group
        obj["organization"] = self.organization
        obj["status_time_display"] = self.status_time_display
        obj["medal"] = self.medal
        obj["balloon_color"] = self.balloon_color
        obj["logo"] = self.logo

        return obj

    @property
    def __json__(self):
        return json.dumps(self.__dict__)
