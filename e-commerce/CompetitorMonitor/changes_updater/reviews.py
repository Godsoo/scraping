from join_computation import ChangeJoinComputation
from changes import Change

class MergeReviews(ChangeJoinComputation):
    accept_codes = [Change.UPDATE]

    def process_res(self, result):
        result.merge_reviews()
