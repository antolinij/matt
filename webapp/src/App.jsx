import { useState, useEffect } from "react";
import { api } from "./api";

const today = new Date().toISOString().slice(0, 10);

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

export default function App() {
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [showRegister, setShowRegister] = useState(false);

  // Login/Register form
  const [authForm, setAuthForm] = useState({
    username: "",
    password: "",
    email: "",
    fullName: ""
  });

  const [schools, setSchools] = useState([]);
  const [students, setStudents] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [payments, setPayments] = useState([]);
  const [status, setStatus] = useState(null);

  const [schoolForm, setSchoolForm] = useState({ name: "", email: "" });
  const [studentForm, setStudentForm] = useState({ school_id: "", first_name: "", last_name: "", email: "" });
  const [invoiceForm, setInvoiceForm] = useState({ student_id: "", amount: "", issue_date: today, due_date: today, description: "" });
  const [paymentForm, setPaymentForm] = useState({ invoice_id: "", amount: "", payment_date: today, payment_method: "cash", reference: "" });

  const [schoolStatusId, setSchoolStatusId] = useState("");
  const [studentStatusId, setStudentStatusId] = useState("");

  // Check authentication on mount
  useEffect(() => {
    if (api.isAuthenticated()) {
      setIsAuthenticated(true);
      // Optionally fetch current user info
      api.getCurrentUser()
        .then(setUser)
        .catch(() => {
          // Token invalid, logout
          setIsAuthenticated(false);
          api.logout();
        });
    }
  }, []);

  async function run(action, successText) {
    setError("");
    setMessage("");
    try {
      await action();
      if (successText) setMessage(successText);
    } catch (err) {
      setError(err.message);
      // If session expired, logout
      if (err.message.includes("Session expired")) {
        setIsAuthenticated(false);
        setUser(null);
      }
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await api.login(authForm.username, authForm.password);
      const currentUser = await api.getCurrentUser();
      setUser(currentUser);
      setIsAuthenticated(true);
      setAuthForm({ username: "", password: "", email: "", fullName: "" });
      setMessage("Login successful!");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await api.register(authForm.username, authForm.email, authForm.password, authForm.fullName);
      setMessage("Registration successful! Please login.");
      setShowRegister(false);
      setAuthForm({ username: "", password: "", email: "", fullName: "" });
    } catch (err) {
      setError(err.message);
    }
  }

  function handleLogout() {
    api.logout();
    setIsAuthenticated(false);
    setUser(null);
    setMessage("Logged out successfully");
  }

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="page">
        <header>
          <h1>Mattilda Mini Client</h1>
          <p>Connected to <code>{api.baseUrl}</code></p>
        </header>

        {message && <div className="banner ok">{message}</div>}
        {error && <div className="banner err">{error}</div>}

        <section className="card" style={{ maxWidth: "500px", margin: "2rem auto" }}>
          <h2>{showRegister ? "Register" : "Login"}</h2>

          {!showRegister ? (
            <form onSubmit={handleLogin}>
              <input
                placeholder="Username"
                value={authForm.username}
                onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })}
                required
                autoComplete="username"
              />
              <input
                type="password"
                placeholder="Password"
                value={authForm.password}
                onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                required
                autoComplete="current-password"
              />
              <div style={{ display: "flex", gap: "1rem" }}>
                <button type="submit">Login</button>
                <button type="button" onClick={() => setShowRegister(true)}>
                  Need an account?
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleRegister}>
              <input
                placeholder="Username"
                value={authForm.username}
                onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })}
                required
                autoComplete="username"
              />
              <input
                type="email"
                placeholder="Email"
                value={authForm.email}
                onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                required
                autoComplete="email"
              />
              <input
                placeholder="Full Name"
                value={authForm.fullName}
                onChange={(e) => setAuthForm({ ...authForm, fullName: e.target.value })}
                required
                autoComplete="name"
              />
              <input
                type="password"
                placeholder="Password"
                value={authForm.password}
                onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                required
                autoComplete="new-password"
              />
              <div style={{ display: "flex", gap: "1rem" }}>
                <button type="submit">Register</button>
                <button type="button" onClick={() => setShowRegister(false)}>
                  Back to Login
                </button>
              </div>
            </form>
          )}
        </section>
      </div>
    );
  }

  // Show main app if authenticated
  return (
    <div className="page">
      <header>
        <h1>Mattilda Mini Client</h1>
        <p>Connected to <code>{api.baseUrl}</code></p>
        {user && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem" }}>
            <span>Logged in as: <strong>{user.username}</strong> ({user.email})</span>
            <button onClick={handleLogout} style={{ padding: "0.5rem 1rem" }}>Logout</button>
          </div>
        )}
      </header>

      {message && <div className="banner ok">{message}</div>}
      {error && <div className="banner err">{error}</div>}

      <section className="card">
        <h2>Schools</h2>
        <form onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            await api.createSchool({ name: schoolForm.name, email: schoolForm.email || null });
            setSchoolForm({ name: "", email: "" });
            setSchools(await api.listSchools());
          }, "School created");
        }}>
          <input placeholder="School name" value={schoolForm.name} onChange={(e) => setSchoolForm({ ...schoolForm, name: e.target.value })} required />
          <input placeholder="School email (optional)" type="email" value={schoolForm.email} onChange={(e) => setSchoolForm({ ...schoolForm, email: e.target.value })} />
          <button type="submit">Create</button>
          <button type="button" onClick={() => run(async () => setSchools(await api.listSchools()))}>Refresh</button>
        </form>
        <pre>{pretty(schools)}</pre>
      </section>

      <section className="card">
        <h2>Students</h2>
        <form onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            await api.createStudent({
              school_id: Number(studentForm.school_id),
              first_name: studentForm.first_name,
              last_name: studentForm.last_name,
              email: studentForm.email || null
            });
            setStudentForm({ school_id: "", first_name: "", last_name: "", email: "" });
            setStudents(await api.listStudents());
          }, "Student created");
        }}>
          <input placeholder="School ID" value={studentForm.school_id} onChange={(e) => setStudentForm({ ...studentForm, school_id: e.target.value })} required />
          <input placeholder="First name" value={studentForm.first_name} onChange={(e) => setStudentForm({ ...studentForm, first_name: e.target.value })} required />
          <input placeholder="Last name" value={studentForm.last_name} onChange={(e) => setStudentForm({ ...studentForm, last_name: e.target.value })} required />
          <input placeholder="Email (optional)" type="email" value={studentForm.email} onChange={(e) => setStudentForm({ ...studentForm, email: e.target.value })} />
          <button type="submit">Create</button>
          <button type="button" onClick={() => run(async () => setStudents(await api.listStudents()))}>Refresh</button>
        </form>
        <pre>{pretty(students)}</pre>
      </section>

      <section className="card">
        <h2>Invoices</h2>
        <form onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            await api.createInvoice({
              student_id: Number(invoiceForm.student_id),
              amount: invoiceForm.amount,
              issue_date: invoiceForm.issue_date,
              due_date: invoiceForm.due_date,
              description: invoiceForm.description || null
            });
            setInvoiceForm({ student_id: "", amount: "", issue_date: today, due_date: today, description: "" });
            setInvoices(await api.listInvoices());
          }, "Invoice created");
        }}>
          <input placeholder="Student ID" value={invoiceForm.student_id} onChange={(e) => setInvoiceForm({ ...invoiceForm, student_id: e.target.value })} required />
          <input placeholder="Amount" type="number" step="0.01" value={invoiceForm.amount} onChange={(e) => setInvoiceForm({ ...invoiceForm, amount: e.target.value })} required />
          <input type="date" value={invoiceForm.issue_date} onChange={(e) => setInvoiceForm({ ...invoiceForm, issue_date: e.target.value })} required />
          <input type="date" value={invoiceForm.due_date} onChange={(e) => setInvoiceForm({ ...invoiceForm, due_date: e.target.value })} required />
          <input placeholder="Description" value={invoiceForm.description} onChange={(e) => setInvoiceForm({ ...invoiceForm, description: e.target.value })} />
          <button type="submit">Create</button>
          <button type="button" onClick={() => run(async () => setInvoices(await api.listInvoices()))}>Refresh</button>
        </form>
        <pre>{pretty(invoices)}</pre>
      </section>

      <section className="card">
        <h2>Payments</h2>
        <form onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            await api.createPayment({
              invoice_id: Number(paymentForm.invoice_id),
              amount: paymentForm.amount,
              payment_date: paymentForm.payment_date,
              payment_method: paymentForm.payment_method,
              reference: paymentForm.reference || null
            });
            setPaymentForm({ invoice_id: "", amount: "", payment_date: today, payment_method: "cash", reference: "" });
            setPayments(await api.listPayments());
          }, "Payment created");
        }}>
          <input placeholder="Invoice ID" value={paymentForm.invoice_id} onChange={(e) => setPaymentForm({ ...paymentForm, invoice_id: e.target.value })} required />
          <input placeholder="Amount" type="number" step="0.01" value={paymentForm.amount} onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })} required />
          <input type="date" value={paymentForm.payment_date} onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })} required />
          <select value={paymentForm.payment_method} onChange={(e) => setPaymentForm({ ...paymentForm, payment_method: e.target.value })}>
            <option value="cash">cash</option>
            <option value="card">card</option>
            <option value="transfer">transfer</option>
            <option value="other">other</option>
          </select>
          <input placeholder="Reference" value={paymentForm.reference} onChange={(e) => setPaymentForm({ ...paymentForm, reference: e.target.value })} />
          <button type="submit">Create</button>
          <button type="button" onClick={() => run(async () => setPayments(await api.listPayments()))}>Refresh</button>
        </form>
        <pre>{pretty(payments)}</pre>
      </section>

      <section className="card">
        <h2>Account Status</h2>
        <div className="status-grid">
          <form onSubmit={(e) => {
            e.preventDefault();
            run(async () => setStatus(await api.getSchoolAccountStatus(Number(schoolStatusId))));
          }}>
            <input placeholder="School ID" value={schoolStatusId} onChange={(e) => setSchoolStatusId(e.target.value)} required />
            <button type="submit">Get School Status</button>
          </form>
          <form onSubmit={(e) => {
            e.preventDefault();
            run(async () => setStatus(await api.getStudentAccountStatus(Number(studentStatusId))));
          }}>
            <input placeholder="Student ID" value={studentStatusId} onChange={(e) => setStudentStatusId(e.target.value)} required />
            <button type="submit">Get Student Status</button>
          </form>
        </div>
        <pre>{pretty(status)}</pre>
      </section>
    </div>
  );
}
