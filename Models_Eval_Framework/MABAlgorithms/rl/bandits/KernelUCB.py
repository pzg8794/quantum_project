import numpy as np
from collections import deque
from ..interface.bandit import ContextualMultiArmedBandit
'''
Class for KernelUCB with online updates
https://arxiv.org/pdf/1309.6869
Arguments - <>
'''
class KernelUCB(ContextualMultiArmedBandit):
    '''
    Constructor
    Arguments - <Number of Arms, Size of Context Vector, Gamma, Eta (η), Kernel Function>
    '''

    def __init__(self, n_arms, n_features, gamma, eta, kern,
                 max_history=2000, memlog_every=500, jitter=1e-10):
        self.n_arms      = int(n_arms)
        self.n_features  = int(n_features)
        self.gamma       = float(gamma)
        self.eta         = float(eta)
        self.kern        = kern
        self.jitter      = float(jitter)

        # UCB stats
        self.u     = np.zeros(self.n_arms, dtype=float)
        self.sigma = np.zeros(self.n_arms, dtype=float)

        # Bounded buffers
        self.max_history = int(max_history)
        self.pulled  = deque(maxlen=self.max_history)   # rows: x_t shape (n_features,)
        self.rewards = deque(maxlen=self.max_history)   # scalars

        # Running stats (avoid per-arm unbounded lists)
        self.arm_counts = np.zeros(self.n_arms, dtype=int)
        self.arm_sums   = np.zeros(self.n_arms, dtype=float)

        # Optional bounded histories
        self.totalRewardHistory = deque(maxlen=self.max_history)
        self.regretHistory      = deque(maxlen=self.max_history)

        # Single inverse of K = K(X,X) + gamma I (t x t)
        self.Kinv_current = None

        # Bookkeeping
        self.last_choice = 0
        self.context     = None
        self.tround      = 0

        # Telemetry
        self._memlog_every  = int(memlog_every)  # 0 disables
        self._rebuild_count = 0
        self._kern_validated = False

        # Optional sanity warning
        if self.max_history > 5000:
            print(f"[KernelUCB] WARNING: max_history={self.max_history} may use significant memory. "
                  f"Consider <= 2000 unless you need longer windows.")

    # ---------- utils ----------

    def _coerce_context(self, context):
        """Ensure context has shape (n_arms, n_features)."""
        ctx = np.asarray(context)
        if ctx.ndim == 1:
            if ctx.size < self.n_features:
                row = np.pad(ctx, (0, self.n_features - ctx.size))
            else:
                row = ctx[:self.n_features]
            ctx = np.tile(row.reshape(1, -1), (self.n_arms, 1))
        else:
            if ctx.shape[1] != self.n_features:
                if ctx.shape[1] > self.n_features:
                    ctx = ctx[:, :self.n_features]
                else:
                    pad = np.zeros((ctx.shape[0], self.n_features - ctx.shape[1]))
                    ctx = np.hstack([ctx, pad])
            if ctx.shape[0] != self.n_arms:
                if ctx.shape[0] < self.n_arms:
                    add = np.tile(ctx[-1:], (self.n_arms - ctx.shape[0], 1))
                    ctx = np.vstack([ctx, add])
                else:
                    ctx = ctx[:self.n_arms]
        return ctx

    def _maybe_memlog(self):
        if self._memlog_every > 0 and (len(self.pulled) % self._memlog_every == 0) and len(self.pulled) > 0:
            try:
                import psutil
                mb = psutil.Process().memory_info().rss / (1024 * 1024)
                print(f"[KernelUCB] step={len(self.pulled)}  RSS={mb:.1f} MB  rebuilds={self._rebuild_count}")
            except Exception:
                pass

    def _validate_kernel_once(self):
        """Light validation of kernel API/shape on first run."""
        if self._kern_validated or self.context is None:
            return
        x = self.context[:1]
        kxx = self.kern(x, x)
        if not (np.ndim(kxx) in (0, 2) and (np.ndim(kxx) == 0 or kxx.shape == (1, 1))):
            raise ValueError("kern(x, x) must return a scalar or (1,1) array.")
        self._kern_validated = True

    # ---------- core API ----------

    def run(self, context=None, **kwargs):
        """
        Choose an arm given current context.
        Builds/updates the inverse if sizes changed; otherwise reuses it.
        Uses cached kernel rows for all arms to reduce kernel calls.
        """
        self.tround = kwargs.get('tround', self.tround)
        self.context = self._coerce_context(context)
        self._validate_kernel_once()

        # Cold-start: optimistic UCB
        if len(self.pulled) == 0:
            self.u.fill(1.0)
            action = int(np.random.randint(self.n_arms))
            self.last_choice = action
            return action

        # Design matrices
        X_prev = np.vstack(self.pulled)                                   # (t, d)
        y_prev = np.asarray(self.rewards, dtype=float).reshape(-1, 1)     # (t, 1)
        t = X_prev.shape[0]

        # Build or rebuild inverse if needed (e.g., after buffer wrap)
        if (self.Kinv_current is None) or (self.Kinv_current.shape[0] != t):
            K = self.kern(X_prev, X_prev)
            # Diagonal jitter + ridge
            np.fill_diagonal(K, K.diagonal() + self.gamma + self.jitter)
            self.Kinv_current = np.linalg.pinv(K)
            self._rebuild_count += 1

        Kinv = self.Kinv_current
        y    = y_prev

        # Cache k(context, X_prev) once: shape (n_arms, t)
        k_matrix = self.kern(self.context, X_prev)

        # Compute UCBs
        for i in range(self.n_arms):
            k_i = k_matrix[i].reshape(-1, 1)                               # (t, 1)
            mu  = float(k_i.T @ Kinv @ y)                                  # scalar
            kxx = self.kern(self.context[i:i+1], self.context[i:i+1])
            kxx = float(kxx) if np.ndim(kxx) == 0 else float(kxx.ravel()[0])
            var = kxx - float(k_i.T @ Kinv @ k_i)
            var = max(var, 1e-12)                                          # numeric floor
            self.sigma[i] = np.sqrt(var)
            self.u[i] = mu + (self.eta / np.sqrt(self.gamma)) * self.sigma[i]

        action = int(np.random.choice(np.where(self.u == np.max(self.u))[0]))
        self.last_choice = action
        return action

    def update(self, reward):
        """
        Online update with rank-one block inverse update (SMW block form).
        If buffer size changed (e.g., deque wrapped), rebuild from scratch.
        """
        arm = int(self.last_choice)
        r   = float(reward)

        # Running stats
        self.arm_counts[arm] += 1
        self.arm_sums[arm]   += r

        # Optional regret logging from running means (bounded)
        counts = np.maximum(self.arm_counts, 1)
        means  = self.arm_sums / counts
        optimal = float(np.max(means)) if self.arm_counts.sum() > 0 else 0.0
        self.totalRewardHistory.append(r)
        self.regretHistory.append(optimal - r)

        # Append pulled x_t (already coerced in run)
        x_t = self.context[arm].reshape(-1)   # (d,)
        self.pulled.append(x_t)
        self.rewards.append(r)

        # Telemetry
        self._maybe_memlog()

        # Inverse maintenance
        t = len(self.rewards)
        if t == 1:
            kxx = self.kern(x_t.reshape(1, -1), x_t.reshape(1, -1))
            kxx = float(kxx) if np.ndim(kxx) == 0 else float(kxx.ravel()[0])
            self.Kinv_current = np.array([[1.0 / (kxx + self.gamma + self.jitter)]], dtype=float)
            return

        # If previous inverse doesn't match t-1 (e.g., rebuild case), rebuild full Kinv
        if (self.Kinv_current is None) or (self.Kinv_current.shape[0] != (t - 1)):
            X_prev = np.vstack(self.pulled)[:-1]                     # (t-1, d)
            K = self.kern(X_prev, X_prev)
            np.fill_diagonal(K, K.diagonal() + self.gamma + self.jitter)
            self.Kinv_current = np.linalg.pinv(K)
            self._rebuild_count += 1

        # Rank-one block update to add new point
        Kinv_prev = self.Kinv_current
        X_prev    = np.vstack(self.pulled)[:-1]                       # (t-1, d)
        k_vec     = self.kern(x_t.reshape(1, -1), X_prev).reshape(-1, 1)  # (t-1, 1)
        kxx       = self.kern(x_t.reshape(1, -1), x_t.reshape(1, -1))
        kxx       = float(kxx) if np.ndim(kxx) == 0 else float(kxx.ravel()[0])
        kxx      += self.gamma + self.jitter

        # Schur complement guard
        s_denom = kxx - float(k_vec.T @ Kinv_prev @ k_vec)
        if s_denom <= 1e-12:
            s_denom = 1e-12
        s = 1.0 / s_denom

        # Block inverse:
        # [[Kinv_prev + s*Kinv_prev*k*k^T*Kinv_prev,   -s*Kinv_prev*k],
        #  [(-s*Kinv_prev*k)^T,                        s            ]]
        K11 = Kinv_prev + s * (Kinv_prev @ k_vec @ k_vec.T @ Kinv_prev)
        K12 = -s * (Kinv_prev @ k_vec)
        K21 = K12.T
        K22 = np.array([[s]])

        self.Kinv_current = np.vstack([np.hstack([K11, K12]),
                                       np.hstack([K21, K22])])

    def regretBound(self, T):
        return self.n_features * np.sqrt(T * np.log((1 + T) / self.gamma))
