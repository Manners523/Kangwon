"""결정 규칙. 실험에서 정책을 바꿔 끼울 수 있게 값만 담는다.

기본값은 '파일럿용 고정 규칙'이다. 무엇이 발롱도르에 유리한지는 아직 모르므로 최적화된 값이 아니다.
무작위 항목은 seed 로 재현 가능하게 하고, 고른 값은 항상 로그에 남는다.
"""
import random
from dataclasses import asdict, dataclass, field


@dataclass
class Policy:
    name: str = "pilot-default"
    seed: int = 1
    turning_point: str = "random"      # random | first | last  (전환점 팝업의 선택지)
    contract: str = "stay"             # stay | best_offer       (프로 구단 계약/진로)
    youth_path: str = "club"           # club | school            (고교 -> 유스 구단 제안 vs 진급)
    nt_callup: str = "join"            # join | decline            (대표팀 소집)
    match_view: str = "result_only"    # result_only | watch       (결승 등 경기 연출)
    style_index: int = -1              # 플레이 스타일 후보 번호, -1 이면 무작위
    focus: list = field(default_factory=lambda: ["슈팅", "피지컬"])  # 집중 육성 능력치 2개
    career_name: str = "exp-001"
    rng: random.Random = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self.rng is None:
            self.rng = random.Random(self.seed)

    def as_dict(self):
        d = asdict(self)
        d.pop("rng", None)
        return d
