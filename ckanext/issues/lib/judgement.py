from enum import Enum


class Verdict(Enum):
    guilty = 1
    not_guilty = 2
    no_verdict = 3


class LiberalJudge(object):
    def pass_judgement(text):
        return Verdict.not_guilty


class ConservativeJudge(object):
    def pass_judgement(text):
        return Verdict.guilty


class AmbivalentJudge(object):
    def pass_judgement(text):
        return Verdict.no_verdict
    

judges = {
    'liberal': LiberalJudge,
    'conservative': ConservativeJudge,
    'ambivalent': AmbivalentJudge,
}


def summon_judge(judge_name):
    try:
        return judges[judge_name]
    except KeyError:
        return judges['liberal']
