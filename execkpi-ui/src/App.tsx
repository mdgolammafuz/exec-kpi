import { useEffect, useState } from "react";
import
  {
    runSQL,
    getABSample,
    runABTest,
    trainML,
    latestML,
    getShap,
  } from "./api";
import type {
  KPIResponse,
  ABSampleResponse,
  ABTestResult,
  ShapSummary,
} from "./api";

type Tab = "kpi" | "ab" | "ml";

const KPI_SQL_FILES = [
  "api_revenue_daily.sql",
  "api_funnel_users.sql",
  "api_ab_group.sql",
  "api_ab_metrics.sql",
  "api_retention_weekly.sql",
  "api_features_conversion.sql",
];

type TabState = {
  output: unknown;
  error: string | null;
};

type ABStatus = { status: "running-ab-test"; alpha: number };

function App ()
{
  const [ tab, setTab ] = useState<Tab>( "kpi" );

  // separate buckets for each tab
  const [ tabData, setTabData ] = useState<Record<Tab, TabState>>( {
    kpi: { output: null, error: null },
    ab: { output: null, error: null },
    ml: { output: null, error: null },
  } );

  const setTabOutput = ( which: Tab, output: unknown ) =>
  {
    setTabData( ( prev ) => ( {
      ...prev,
      [ which ]: { ...prev[ which ], output, error: null },
    } ) );
  };

  const setTabError = ( which: Tab, error: string | null ) =>
  {
    setTabData( ( prev ) => ( {
      ...prev,
      [ which ]: { ...prev[ which ], error },
    } ) );
  };

  const current = tabData[ tab ];

  return (
    <div
      style={ {
        maxWidth: 1180,
        margin: "0 auto",
        padding: "2.25rem 1.5rem 3rem",
        background: "#f3f4f6",
        minHeight: "100vh",
      } }
    >
      <header style={ { marginBottom: "1.5rem" } }>
        <h1 style={ { fontSize: "1.9rem", marginBottom: "0.25rem" } }>
          ExecKPI — Data Gov UI
        </h1>
        <p style={ { color: "#4b5563", fontSize: "0.95rem" } }>
          React → FastAPI → BigQuery → dbt → ML. Three panels, one backend.
        </p>
      </header>

      <div
        style={ {
          display: "flex",
          gap: "0.75rem",
          marginBottom: "1.5rem",
        } }
      >
        <TabButton active={ tab === "kpi" } onClick={ () => setTab( "kpi" ) }>
          KPI
        </TabButton>
        <TabButton active={ tab === "ab" } onClick={ () => setTab( "ab" ) }>
          A/B
        </TabButton>
        <TabButton active={ tab === "ml" } onClick={ () => setTab( "ml" ) }>
          ML
        </TabButton>
      </div>

      <div
        style={ {
          background: "#fff",
          border: "1px solid #e5e7eb",
          borderRadius: "0.75rem",
          padding: "1.25rem 1.25rem 1rem",
          marginBottom: "1.4rem",
          boxShadow: "0 10px 15px -10px rgba(0,0,0,0.12)",
        } }
      >
        { tab === "kpi" && (
          <KPIPanel
            setOutput={ ( d ) => setTabOutput( "kpi", d ) }
            setError={ ( e ) => setTabError( "kpi", e ) }
          />
        ) }
        { tab === "ab" && (
          <ABPanel
            setOutput={ ( d ) => setTabOutput( "ab", d ) }
            setError={ ( e ) => setTabError( "ab", e ) }
          />
        ) }
        { tab === "ml" && (
          <MLPanel
            setOutput={ ( d ) => setTabOutput( "ml", d ) }
            setError={ ( e ) => setTabError( "ml", e ) }
          />
        ) }
      </div>

      <section>
        <h2 style={ { marginBottom: "0.5rem", fontSize: "1.1rem" } }>Result</h2>
        { current.error ? (
          <pre
            style={ {
              background: "#fef2f2",
              padding: "1rem",
              border: "1px solid #fca5a5",
              borderRadius: "0.5rem",
              color: "#b91c1c",
              fontSize: "0.83rem",
            } }
          >
            { current.error }
          </pre>
        ) : (
          <pre
            style={ {
              background: "#0f172a",
              color: "#e2e8f0",
              padding: "1rem",
              minHeight: "170px",
              overflow: "auto",
              borderRadius: "0.5rem",
              fontSize: "0.8rem",
              lineHeight: 1.4,
              border: "1px solid #0f172a",
            } }
          >
            { current.output
              ? JSON.stringify( current.output, null, 2 )
              : "No output yet." }
          </pre>
        ) }
      </section>
    </div>
  );
}

function KPIPanel ( {
  setOutput,
  setError,
}: {
  setOutput: ( d: KPIResponse | { status: string } ) => void;
  setError: ( m: string | null ) => void;
} )
{
  const [ start, setStart ] = useState<string>( () =>
    new Date( Date.now() - 30 * 86400000 ).toISOString().slice( 0, 10 ),
  );
  const [ end, setEnd ] = useState<string>( () =>
    new Date().toISOString().slice( 0, 10 ),
  );
  const [ sqlFile, setSqlFile ] = useState<string>( "api_revenue_daily.sql" );
  const [ loading, setLoading ] = useState( false );

  const fetchKPI = () =>
  {
    setLoading( true );
    setError( null );
    setOutput( { status: "loading-kpi" } );
    runSQL( sqlFile, [
      { name: "start", type: "DATE", value: start },
      { name: "end", type: "DATE", value: end },
    ] )
      .then( ( data ) => setOutput( data ) )
      .catch( ( err: unknown ) =>
        setError( err instanceof Error ? err.message : "Request failed" ),
      )
      .finally( () => setLoading( false ) );
  };

  return (
    <div>
      <h2 style={ { fontSize: "1.05rem", marginBottom: "1rem" } }>KPI</h2>
      <div
        style={ {
          display: "flex",
          gap: "0.75rem",
          flexWrap: "wrap",
          alignItems: "center",
        } }
      >
        <label style={ { fontSize: "0.8rem", color: "#374151" } }>
          SQL
          <select
            value={ sqlFile }
            onChange={ ( e ) => setSqlFile( e.target.value ) }
            style={ {
              marginTop: "0.25rem",
              padding: "0.35rem 0.4rem",
              border: "1px solid #d1d5db",
              borderRadius: "0.4rem",
              minWidth: "210px",
            } }
          >
            { KPI_SQL_FILES.map( ( f ) => (
              <option key={ f } value={ f }>
                { f }
              </option>
            ) ) }
          </select>
        </label>
        <label style={ { fontSize: "0.8rem", color: "#374151" } }>
          Start
          <input
            type="date"
            value={ start }
            onChange={ ( e ) => setStart( e.target.value ) }
            style={ {
              marginTop: "0.25rem",
              padding: "0.3rem 0.4rem",
              border: "1px solid #d1d5db",
              borderRadius: "0.4rem",
            } }
          />
        </label>
        <label style={ { fontSize: "0.8rem", color: "#374151" } }>
          End
          <input
            type="date"
            value={ end }
            onChange={ ( e ) => setEnd( e.target.value ) }
            style={ {
              marginTop: "0.25rem",
              padding: "0.3rem 0.4rem",
              border: "1px solid #d1d5db",
              borderRadius: "0.4rem",
            } }
          />
        </label>
        <button
          onClick={ fetchKPI }
          disabled={ loading }
          style={ {
            background: loading ? "#94a3b8" : "#1f2937",
            color: "#fff",
            border: "none",
            padding: "0.5rem 1.05rem",
            borderRadius: "0.45rem",
            fontWeight: 500,
            cursor: loading ? "not-allowed" : "pointer",
            marginTop: "0.5rem",
          } }
        >
          { loading ? "Loading…" : "Run" }
        </button>
      </div>
    </div>
  );
}

function ABPanel ( {
  setOutput,
  setError,
}: {
  setOutput: ( d: ABSampleResponse | ABTestResult | ABStatus ) => void;
  setError: ( m: string | null ) => void;
} )
{
  const [ sample, setSample ] = useState<ABSampleResponse[ "sample" ] | null>( null );
  const [ alpha, setAlpha ] = useState<number>( 0.05 );
  const [ loading, setLoading ] = useState<boolean>( true );
  const [ testing, setTesting ] = useState<boolean>( false );
  const [ panelError, setPanelError ] = useState<string | null>( null );

  // load once on mount
  useEffect( () =>
  {
    const fetchSample = async () =>
    {
      setLoading( true );
      setPanelError( null );
      try
      {
        const data = await getABSample();
        setSample( data.sample );
        setOutput( data );
      } catch ( err )
      {
        const msg = err instanceof Error ? err.message : "Request failed";
        setPanelError( msg );
      } finally
      {
        setLoading( false );
      }
    };
    void fetchSample();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [] );

  const runTest = () =>
  {
    if ( !sample?.A || !sample?.B )
    {
      setPanelError( "Sample not loaded yet. Please retry." );
      return;
    }
    setPanelError( null );
    setError( null );
    setTesting( true );

    // show in result area that we’re running a new test
    setOutput( { status: "running-ab-test", alpha } );

    runABTest( {
      a_success: sample.A.success,
      a_total: sample.A.total,
      b_success: sample.B.success,
      b_total: sample.B.total,
      alpha,
    } )
      .then( ( data ) =>
      {
        setOutput( data );
      } )
      .catch( ( err: unknown ) =>
      {
        const msg = err instanceof Error ? err.message : "Request failed";
        setPanelError( msg );
        setError( msg );
      } )
      .finally( () => setTesting( false ) );
  };

  const retryFetch = () =>
  {
    setLoading( true );
    setPanelError( null );
    getABSample()
      .then( ( data ) =>
      {
        setSample( data.sample );
        setOutput( data );
      } )
      .catch( ( err: unknown ) =>
      {
        const msg = err instanceof Error ? err.message : "Request failed";
        setPanelError( msg );
      } )
      .finally( () => setLoading( false ) );
  };

  return (
    <div>
      <h2 style={ { fontSize: "1.05rem", marginBottom: "1rem" } }>A/B</h2>
      { loading ? (
        <p style={ { color: "#6b7280" } }>Loading A/B sample…</p>
      ) : panelError ? (
        <div>
          <p style={ { color: "crimson", marginBottom: "0.5rem" } }>
            Couldn’t load sample.
          </p>
          <button
            onClick={ retryFetch }
            style={ {
              background: "#1f2937",
              color: "#fff",
              border: "none",
              padding: "0.45rem 0.9rem",
              borderRadius: "0.35rem",
              cursor: "pointer",
            } }
          >
            Retry
          </button>
        </div>
      ) : sample ? (
        <>
          <p style={ { marginBottom: "0.6rem" } }>
            A: { sample.A.success }/{ sample.A.total } | B: { sample.B.success }/
            { sample.B.total }
          </p>
          <div
            style={ { display: "flex", alignItems: "center", gap: "0.5rem" } }
          >
            <label style={ { fontSize: "0.8rem", color: "#374151" } }>
              alpha
              <input
                type="number"
                step="0.01"
                min="0.01"
                max="0.2"
                value={ alpha }
                onChange={ ( e ) => setAlpha( parseFloat( e.target.value ) ) }
                style={ {
                  marginLeft: "0.5rem",
                  padding: "0.25rem 0.35rem",
                  width: "5rem",
                  border: "1px solid #d1d5db",
                  borderRadius: "0.4rem",
                } }
              />
            </label>
            <button
              onClick={ runTest }
              style={ {
                background: testing ? "#94a3b8" : "#1f2937",
                color: "#fff",
                border: "none",
                padding: "0.45rem 0.9rem",
                borderRadius: "0.35rem",
                cursor: testing ? "not-allowed" : "pointer",
              } }
              disabled={ testing }
            >
              { testing ? "Running…" : "Run test" }
            </button>
          </div>
          { testing ? (
            <p style={ { color: "#6b7280", marginTop: "0.3rem" } }>
              Testing with α = { alpha } …
            </p>
          ) : null }
        </>
      ) : (
        <p style={ { color: "#777" } }>No sample returned.</p>
      ) }
    </div>
  );
}

// small helper to avoid `any` for axios-like errors
function isAxiosLike404 ( err: unknown ): boolean
{
  if ( typeof err !== "object" || err === null ) return false;
  if ( !( "response" in err ) ) return false;
  const resp = ( err as { response?: unknown } ).response;
  if ( typeof resp !== "object" || resp === null ) return false;
  const status = ( resp as { status?: unknown } ).status;
  return typeof status === "number" && status === 404;
}

function MLPanel ( {
  setOutput,
  setError,
}: {
  setOutput: ( d: unknown ) => void;
  setError: ( m: string | null ) => void;
} )
{
  const [ training, setTraining ] = useState( false );
  const [ loadingLatest, setLoadingLatest ] = useState( false );
  const [ loadingShap, setLoadingShap ] = useState( false );
  const [ panelError, setPanelError ] = useState<string | null>( null );

  const handleTrain = () =>
  {
    setTraining( true );
    setPanelError( null );
    setError( null );
    trainML()
      .then( ( data ) => setOutput( data ) )
      .catch( ( err: unknown ) =>
      {
        const msg = err instanceof Error ? err.message : "Request failed";
        setPanelError( msg );
        setError( msg );
      } )
      .finally( () => setTraining( false ) );
  };

  const handleLatest = () =>
  {
    setLoadingLatest( true );
    setPanelError( null );
    setError( null );
    latestML()
      .then( ( data ) => setOutput( data ) )
      .catch( ( err: unknown ) =>
      {
        const msg = err instanceof Error ? err.message : "Request failed";
        setPanelError( msg );
        setError( msg );
      } )
      .finally( () => setLoadingLatest( false ) );
  };

  const handleShap = () =>
  {
    setLoadingShap( true );
    setPanelError( null );
    setError( null );
    getShap()
      .then( ( data: ShapSummary ) =>
      {
        setOutput( data );
      } )
      .catch( ( err: unknown ) =>
      {
        const msg = isAxiosLike404( err )
          ? "No SHAP summary yet. Train a model first."
          : err instanceof Error
            ? err.message
            : "Request failed";
        setPanelError( msg );
        setError( msg );
      } )
      .finally( () => setLoadingShap( false ) );
  };

  return (
    <div>
      <h2 style={ { fontSize: "1.05rem", marginBottom: "1rem" } }>ML</h2>
      <div style={ { display: "flex", gap: "0.55rem", flexWrap: "wrap" } }>
        <button
          onClick={ handleTrain }
          disabled={ training }
          style={ {
            background: training ? "#94a3b8" : "#1f2937",
            color: "#fff",
            border: "none",
            padding: "0.45rem 0.95rem",
            borderRadius: "0.45rem",
            cursor: training ? "not-allowed" : "pointer",
          } }
        >
          { training ? "Training…" : "Train (BQ → xgboost)" }
        </button>
        <button
          onClick={ handleLatest }
          style={ {
            background: loadingLatest ? "#94a3b8" : "#334155",
            color: "#fff",
            border: "none",
            padding: "0.45rem 0.95rem",
            borderRadius: "0.45rem",
            cursor: loadingLatest ? "not-allowed" : "pointer",
          } }
          disabled={ loadingLatest }
        >
          { loadingLatest ? "Loading latest…" : "Latest" }
        </button>
        <button
          onClick={ handleShap }
          style={ {
            background: loadingShap ? "#94a3b8" : "#475569",
            color: "#fff",
            border: "none",
            padding: "0.45rem 0.95rem",
            borderRadius: "0.45rem",
            cursor: loadingShap ? "not-allowed" : "pointer",
          } }
          disabled={ loadingShap }
        >
          { loadingShap ? "Loading SHAP…" : "SHAP" }
        </button>
      </div>
      { panelError ? (
        <p style={ { color: "crimson", marginTop: "0.5rem" } }>{ panelError }</p>
      ) : (
        <p style={ { color: "#6b7280", marginTop: "0.5rem" } }>
          Uses artifacts/metrics.json and artifacts/shap_summary.json from
          backend.
        </p>
      ) }
    </div>
  );
}

function TabButton ( {
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
} )
{
  return (
    <button
      onClick={ onClick }
      disabled={ active }
      style={ {
        background: active ? "#0f172a" : "#e2e8f0",
        color: active ? "#fff" : "#0f172a",
        border: "none",
        padding: "0.55rem 1.2rem",
        borderRadius: "0.6rem",
        fontWeight: 500,
        cursor: active ? "default" : "pointer",
        fontSize: "0.9rem",
      } }
    >
      { children }
    </button>
  );
}

export default App;
