"""
Связка микроуровня и макроуровня. Сердце модели.

Здесь поведение отдельных агентов сворачивается в единый скаляр системного
напряжения, который управляет марковским ядром. Связка состоит из трёх
звеньев, и в каждом заложена содержательная глубина, а не техническая.

Первое звено, агрегация. Действия агентов суммируются не поровну, а с весами
исходящей силы влияния из матрицы межагентных связей. Действие мощного и
втянутого во множество враждебных диад государства весит для системы больше,
чем действие слабого. КНР доминирует в агрегате, как и в реальной динамике
региона.

Второе звено, дифференцированная память. Система помнит прошлое по-разному
для разных измерений. Риторика летуча и забывается быстро, военные расходы
инерционны, институциональный дрейф почти необратим, ибо институты не
откатываются назад. Три коэффициента забывания вместо одного суть
динамическая формализация необратимости эрозии правовых ограничений на
применение силы. Отсюда же в систему приходит гистерезис: накопленный
институциональный сдвиг удерживает напряжение даже после того, как видимое
поведение успокоилось.

Третье звено, логистический синтез. Сглаженные компоненты сворачиваются в
напряжение через сигмоиду с весами beta. Милитаризация весит тяжелее
риторики, реализм отдаёт первенство материальному, нормативный сдвиг почти
равен ему по весу.

Пороги фазовых переходов. Синтез задаёт отображение поведения в напряжение,
марковское ядро задаёт отображение напряжения в режим. Их сцепление через
стационарное распределение цепи даёт вычислимые пороги напряжения, при
которых система меняет долгосрочный аттрактор. Это операционализация
центрального тезиса о вычислимых порогах фазовых переходов в региональном
комплексе безопасности.
"""

from __future__ import annotations
import numpy as np

from engine.influence import INFLUENCE, CODES


COMPONENTS = ("milex", "rhet", "drift")


def influence_weights() -> dict:
    """Веса агрегации из исходящей силы влияния агентов, нормированные."""
    strength = {i: sum(INFLUENCE.W[i][j] for j in CODES) for i in CODES}
    total = sum(strength.values())
    return {i: strength[i] / total for i in CODES}


def aggregate(actions: dict, weights: dict = None) -> dict:
    """
    Сворачивает действия агентов в три системных компонента. actions суть
    словарь код -> вектор действия. weights по умолчанию из силы влияния.
    """
    w = weights or influence_weights()
    return {c: sum(w[i] * actions[i][c] for i in CODES) for c in COMPONENTS}


def _sigmoid(x: float) -> float:
    """Логистическая сигмоида с защитой от переполнения."""
    x = float(np.clip(x, -60.0, 60.0))
    return 1.0 / (1.0 + np.exp(-x))


# Веса перцептивного давления по трём измерениям безопасности.
# Восприятие угрозы, дефицит доверия, нормативный распад.
PRESSURE_WEIGHTS = {"threat": 0.40, "distrust": 0.25, "erosion": 0.35}


def perceptual_pressure(states: dict, weights: dict = None) -> float:
    """
    Быстрый контур напряжения. Сворачивает конфигурацию страха, недоверия и
    нормативного распада системы в скаляр, минуя инерционные бюджеты. states
    суть словарь код -> [z1, z2, z3]. Вес агента по силе влияния.

    Этот контур есть конструктивистский слой поверх материального: напряжение
    комплекса безопасности питается не только тем, что государства строят, но
    и тем, насколько остра сама конфигурация угроз. Восприятие меняется
    мгновенно, расходы медленно, оттого контур быстрый и без памяти.
    """
    w = weights or influence_weights()
    pw = PRESSURE_WEIGHTS
    return sum(
        w[i] * (pw["threat"] * states[i][0]
                + pw["distrust"] * (1.0 - states[i][1])
                + pw["erosion"] * states[i][2])
        for i in CODES
    )


class DifferentialMemory:
    """
    Оператор системной памяти H(t) с покомпонентным и асимметричным
    забыванием. Каждое измерение хранит пару коэффициентов: lam_up действует
    при нарастании входа, lam_down при спаде.
        H_c(t) = lam * H_c(t-1) + (1 - lam) * вход_c.
    Чем выше lam, тем медленнее реакция. Совпадение lam_up и lam_down даёт
    обычное симметричное сглаживание для риторики и расходов. У
    институционального дрейфа lam_up низок, а lam_down высок: дрейф
    накапливается быстро и почти не откатывается. Это храповик необратимости.
    """

    def __init__(self, lam=None):
        # Пары (lam_up, lam_down) по измерениям.
        self.lam = lam or {
            "milex": (0.6, 0.6),    # расходы инерционны, симметрично
            "rhet": (0.3, 0.3),     # риторика летуча, симметрично
            "drift": (0.3, 0.95),   # дрейф как храповик, быстро вверх, медленно вниз
        }
        for c, (u, d) in self.lam.items():
            if not (0.0 <= u < 1.0 and 0.0 <= d < 1.0):
                raise ValueError(f"коэффициент забывания {c} вне [0, 1)")
        self.H = {c: 0.0 for c in COMPONENTS}
        self._seeded = False

    def seed(self, components: dict) -> None:
        """Инициализирует память текущим состоянием, снимая холодный старт."""
        self.H = {c: float(components[c]) for c in COMPONENTS}
        self._seeded = True

    def preview(self, components: dict) -> dict:
        """Сглаженное состояние без продвижения памяти, без побочных эффектов."""
        if not self._seeded:
            return {c: float(components[c]) for c in COMPONENTS}
        out = {}
        for c in COMPONENTS:
            x = float(components[c])
            lam = self.lam[c][0] if x >= self.H[c] else self.lam[c][1]
            out[c] = lam * self.H[c] + (1.0 - lam) * x
        return out

    def update(self, components: dict) -> dict:
        """Продвигает память на шаг и возвращает сглаженное состояние."""
        if not self._seeded:
            self.seed(components)
            return dict(self.H)
        self.H = self.preview(components)
        return dict(self.H)

    def reset(self) -> None:
        self.H = {c: 0.0 for c in COMPONENTS}
        self._seeded = False


# Веса синтеза. Смещение beta0 удерживает покоящуюся систему в низком
# напряжении. Контур действий есть материальный слой, контур давления есть
# перцептивный слой. Милитаризация тяжелее риторики.
DEFAULT_BETA = {"b0": -2.035, "milex": 0.7, "rhet": 0.4, "drift": 0.6, "pressure": 2.5}


class LevelCoupling:
    """
    Полная связка уровней. Принимает действия агентов и их состояния, ведёт
    память материального контура и выдаёт системное напряжение для
    марковского ядра. Напряжение есть сумма двух слоёв: медленного
    материального через действия с памятью и быстрого перцептивного через
    конфигурацию состояний.
    """

    def __init__(self, beta: dict = None, memory: DifferentialMemory = None, weights: dict = None):
        self.beta = beta or dict(DEFAULT_BETA)
        self.memory = memory or DifferentialMemory()
        self.weights = weights or influence_weights()

    def _arg(self, smoothed: dict, states: dict) -> float:
        b = self.beta
        material = (b["milex"] * smoothed["milex"] + b["rhet"] * smoothed["rhet"]
                    + b["drift"] * smoothed["drift"])
        perceptual = b["pressure"] * perceptual_pressure(states, self.weights)
        return b["b0"] + material + perceptual

    def tension(self, actions: dict, states: dict) -> float:
        """Системное напряжение в [0, 1] с учётом памяти и конфигурации состояний."""
        comps = aggregate(actions, self.weights)
        smoothed = self.memory.update(comps)
        return _sigmoid(self._arg(smoothed, states))

    def raw_tension(self, actions: dict, states: dict) -> float:
        """Напряжение без продвижения памяти, по мгновенному поведению."""
        comps = aggregate(actions, self.weights)
        smoothed = self.memory.preview(comps)
        return _sigmoid(self._arg(smoothed, states))

    def explain(self, actions: dict, states: dict) -> dict:
        """
        Полный разбор одного шага для прозрачности вычислений. Память при
        этом не продвигается, разбор не имеет побочных эффектов.
        """
        comps = aggregate(actions, self.weights)
        smoothed = self.memory.preview(comps)
        pressure = perceptual_pressure(states, self.weights)
        arg = self._arg(smoothed, states)
        tau = _sigmoid(arg)
        return {
            "components": comps,
            "memory_prev": dict(self.memory.H),
            "smoothed": smoothed,
            "perceptual_pressure": pressure,
            "sigmoid_arg": arg,
            "tension": tau,
        }


# --- Вычислимые пороги фазовых переходов ---

def stationary_distribution(markov, tension: float, iters: int = 4000) -> np.ndarray:
    """Стационарное распределение цепи при фиксированном напряжении."""
    P = markov.transition_matrix(tension)
    pi = np.array([1.0, 1.0, 1.0]) / 3.0
    for _ in range(iters):
        pi = pi @ P
    return pi


def phase_thresholds(markov, grid: int = 2000) -> dict:
    """
    Пороги напряжения, при которых меняется долгосрочный доминирующий режим.
    Реализация центрального тезиса о вычислимых порогах фазовых переходов.
    """
    taus = np.linspace(0.0, 1.0, grid + 1)
    dom = [int(np.argmax(stationary_distribution(markov, t, iters=600))) for t in taus]
    thresholds = {}
    labels = {(0, 1): "S1->S2", (1, 2): "S2->S3"}
    for k in range(1, len(dom)):
        if dom[k] != dom[k - 1]:
            key = (dom[k - 1], dom[k])
            if key in labels:
                # уточнение бинарным поиском в найденном интервале
                a, b = taus[k - 1], taus[k]
                base = dom[k - 1]
                for _ in range(40):
                    m = (a + b) / 2.0
                    if int(np.argmax(stationary_distribution(markov, m, iters=600))) == base:
                        a = m
                    else:
                        b = m
                thresholds[labels[key]] = (a + b) / 2.0
    return thresholds


# Готовая связка со стандартными параметрами.
COUPLING = LevelCoupling()
