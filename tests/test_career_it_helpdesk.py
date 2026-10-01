import unittest

from game.careers import it_helpdesk as M
from tests.office_desk_cases import DeskCases


class ItHelpdeskTests(DeskCases, unittest.TestCase):
    M = M


if __name__ == '__main__':
    unittest.main()
