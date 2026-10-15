---
제목: 의존성 주입(DI) 2편: 스프링은 무엇을 대신 해 주나
---

의존성 주입을 스프링 프레임워크에서 어떻게 활용하고 있는지 보자.

## 진행 버전
- Spring Boot 4.1 
- Kotlin 2.3 (JDK 25)

---

## 스프링 컨테이너가 대신 해 주는 것

**IoC(Inversion of Control) 제어의 역전**: 제어 흐름을 반전시키는 설계 원칙으로 개발자가 직접 제어하는 것이 아니라 프레임워크가 대신 제어하는 것을 의미한다. 

IoC라는 용어는 1988년 Ralph E. Johnson과 Brian Foote가 Journal of Object-Oriented Programming에 게재한 Designing Reusable Classes에서 처음 사용되었다고 한다. (개념 자체는 그 이전에도 있었다고 한다.)

[Designing Reusable Classes](https://www.laputan.org/drc/drc.html)
> One important characteristic of a framework is that the methods defined by the user to tailor the framework will often be called from within the framework itself, rather than from the user's application code. The framework often plays the role of the main program in coordinating and sequencing application activity. This inversion of control gives frameworks the power to serve as extensible skeletons. The methods supplied by the user tailor the generic algorithms defined in the framework for a particular application.
> 
> 프레임워크의 중요한 특징 중 하나는, 사용자가 프레임워크를 자기 용도에 맞추려고 정의한 메소드를 애플리케이션 코드가 아니라 프레임워크가 호출하는 경우가 많다는 것이다. 프레임워크는 흔히 메인 프로그램 역할을 맡아 애플리케이션의 동작을 조율하고 실행 순서를 정한다. 이 제어의 역전 덕분에 프레임워크는 확장 가능한 뼈대 역할을 할 수 있다. 사용자가 작성한 메소드는 프레임워크에 정의된 범용 알고리즘을 각 애플리케이션에 맞게 다듬는다.

**DI(Dependency Injection) 의존성 주입**: IoC를 구현하는 방법 중 하나로, 객체가 필요한 의존성을 외부에서 받는 방식이다. 

**DI 외 다른 IoC 구현 사례**
- 콜백
- 템플릿 메소드 패턴
- 옵저버 패턴 
- ... 등

```kotlin
// DI 사용하지 않을 시
@Service
class OrderFacadeService {
    // 개발자가 직접 생성하여 제어
    private val redisClient = RedisClient()
    private val lockExecutor = DistributedLockExecutor(redisClient)
    private val paymentClient = PaymentClient()
    private val orderRepository = OrderRepository()
    private val orderService = OrderService(orderRepository)
    ...
}

// DI 사용 시
@Service
class OrderFacadeService(
    // 스프링 컨테이너가 생성하여 주입
    private val lockExecutor: DistributedLockExecutor,
    private val paymentClient: PaymentClient,
    private val orderService: OrderService,
) {
    ...
}
```

스프링은 IoC 컨테이너를 사용하여 인스턴스 생성, 연결, 수명 주기, 스코프를 관리하고 생성자 주입(권장 방법. 세터, 필드 주입도 가능)을 통해 의존성 관리를 한다. DI 덕분에 로직 수정 없이 구현체 변경이 가능해지고 IoC 컨테이너 덕분에 생성 및 제어를 직접 할 필요가 없어진다.

### BeanFactory와 ApplicationContext

스프링 IoC 컨테이너의 중심에는 두 인터페이스가 있다.

- **BeanFactory**: 빈을 등록하고, 만들고, 주입하고, 꺼내는 기본 컨테이너
- **ApplicationContext**: BeanFactory를 상속하고 애플리케이션에 필요한 기능을 더한 확장 컨테이너

보통 "스프링 컨테이너"라고 하면 ApplicationContext를 말한다.

**상속하면서, 안에 들고 있다**

ApplicationContext는 BeanFactory를 상속한다(is-a). 그래서 `context.getBean()`을 바로 부를 수 있다. 그런데 구현체인 `GenericApplicationContext`는 빈 관리를 직접 하지 않고, 안에 들고 있는 `DefaultListableBeanFactory`에 맡긴다(has-a). 아래 테스트의 `context.beanFactory.shouldBeInstanceOf<DefaultListableBeanFactory>()`가 이 구조를 확인한다.

**ApplicationContext가 더하는 것**

| 상속한 인터페이스 | 하는 일 | 다시 나오는 곳 |
|---|---|---|
| `ListableBeanFactory` | 타입으로 빈을 여러 개 조회 | 2절 List·Map으로 전부 받기 |
| `HierarchicalBeanFactory` | 부모 컨텍스트 | - |
| `EnvironmentCapable` | 프로퍼티, 프로필 | 1편 마무리의 `@Profile` |
| `MessageSource` | 다국어 메시지 | - |
| `ApplicationEventPublisher` | 이벤트 발행 | 위의 IoC 구현 사례: 옵저버 패턴 |
| `ResourcePatternResolver` | `classpath*:` 같은 패턴으로 리소스 찾기 | 컴포넌트 스캔이 이 기능으로 클래스 파일을 찾는다 |

**언제 만들고, 누가 후처리하나**

기능 목록보다 실무에서 더 와닿는 차이는 이쪽이다.

- **빈을 만드는 시점**: BeanFactory만 쓰면 `getBean()`을 부를 때 빈을 만든다. ApplicationContext는 `refresh()`에서 싱글톤 빈을 미리 만들어 둔다. 그래서 설정이 잘못되면 요청이 들어온 뒤가 아니라 애플리케이션이 뜰 때 실패한다.
- **후처리기 등록**: ApplicationContext는 `BeanFactoryPostProcessor`와 `BeanPostProcessor`를 알아서 등록하고 실행한다. BeanFactory만 쓰면 직접 등록해야 하고, 빠뜨리면 `@Autowired` 어노테이션 처리나 `@Transactional` 같은 기능이 동작하지 않는다.

**실무에서는**

BeanFactory를 직접 쓸 일은 거의 없다. 스프링 부트가 ApplicationContext를 만들어 주고, [스프링 공식 문서](https://docs.spring.io/spring-framework/reference/core/beans/introduction.html)도 특별한 이유가 없다면 ApplicationContext를 쓰라고 권한다. BeanFactory는 직접 쓰는 것이라기보다 ApplicationContext 안에서 실제 일을 하는 부품이다.

아래는 스프링 부트 없이 `GenericApplicationContext`를 직접 써 본 테스트다.

```kotlin
class ApplicationContextTest :
    FunSpec({
        test("GenericApplicationContext 테스트") {
            // given
            val context = GenericApplicationContext()
            // 의존성의 끝단은 가짜로 채운다
            context.registerBean<DistributedLockExecutor> { mockk() }
            context.registerBean<PaymentClient> { mockk() }
            context.registerBean<OrderRepository> { mockk() }
            context.registerBean<UserRepository> { mockk() }
            context.registerBean<ProductRepository> { mockk() }
            context.registerBean<OrderService>()
            context.registerBean<OrderFacadeService>()

            // when
            context.refresh()

            // then
            context.beanDefinitionCount shouldBe 7
            context.beanFactory.shouldBeInstanceOf<DefaultListableBeanFactory>()
            context.getBean<OrderFacadeService>() shouldBeSameInstanceAs context.getBean<OrderFacadeService>()
            context.beanFactory.getDependenciesForBean(OrderFacadeService::class.java.name) shouldContainExactlyInAnyOrder arrayOf(
                DistributedLockExecutor::class.java.name,
                PaymentClient::class.java.name,
                OrderService::class.java.name,
            )
        }
    })
```

#### BeanFactory

```java
public interface BeanFactory {
    Object getBean(String name) throws BeansException;
    <T> T getBean(String name, Class<T> requiredType) throws BeansException;
    Object getBean(String name, @Nullable Object @Nullable ... args) throws BeansException;
    <T> T getBean(Class<T> requiredType) throws BeansException;
    <T> T getBean(Class<T> requiredType, @Nullable Object @Nullable ... args) throws BeansException;

    <T> ObjectProvider<T> getBeanProvider(Class<T> requiredType);
    <T> ObjectProvider<T> getBeanProvider(ResolvableType requiredType);
    <T> ObjectProvider<T> getBeanProvider(ParameterizedTypeReference<T> requiredType);

    boolean containsBean(String name);
    boolean isSingleton(String name) throws NoSuchBeanDefinitionException;
    boolean isPrototype(String name) throws NoSuchBeanDefinitionException;
    boolean isTypeMatch(String name, ResolvableType typeToMatch) throws NoSuchBeanDefinitionException;
    boolean isTypeMatch(String name, Class<?> typeToMatch) throws NoSuchBeanDefinitionException;

    @Nullable Class<?> getType(String name) throws NoSuchBeanDefinitionException;
    @Nullable Class<?> getType(String name, boolean allowFactoryBeanInit) throws NoSuchBeanDefinitionException;

    String[] getAliases(String name);
}
```

#### ApplicationContext

```java
public interface ApplicationContext extends EnvironmentCapable, ListableBeanFactory, HierarchicalBeanFactory,
		MessageSource, ApplicationEventPublisher, ResourcePatternResolver

public class GenericApplicationContext extends AbstractApplicationContext implements BeanDefinitionRegistry {

	private final DefaultListableBeanFactory beanFactory;
    	
	public GenericApplicationContext() {
		this.beanFactory = new DefaultListableBeanFactory();
	}

	public GenericApplicationContext(DefaultListableBeanFactory beanFactory) {
		Assert.notNull(beanFactory, "BeanFactory must not be null");
		this.beanFactory = beanFactory;
	}

    public GenericApplicationContext(@Nullable ApplicationContext parent) {
		this();
		setParent(parent);
	}

	public GenericApplicationContext(DefaultListableBeanFactory beanFactory, ApplicationContext parent) {
		this(beanFactory);
		setParent(parent);
	}

    @Override
	public void setApplicationStartup(ApplicationStartup applicationStartup) {
		super.setApplicationStartup(applicationStartup);
		this.beanFactory.setApplicationStartup(applicationStartup);
	}

    @Override
	public final ConfigurableListableBeanFactory getBeanFactory() {
		return this.beanFactory;
	}

    @Override
	public void registerBeanDefinition(String beanName, BeanDefinition beanDefinition)
			throws BeanDefinitionStoreException {

		this.beanFactory.registerBeanDefinition(beanName, beanDefinition);
	}

	@Override
	public void removeBeanDefinition(String beanName) throws NoSuchBeanDefinitionException {
		this.beanFactory.removeBeanDefinition(beanName);
	}

	@Override
	public BeanDefinition getBeanDefinition(String beanName) throws NoSuchBeanDefinitionException {
		return this.beanFactory.getBeanDefinition(beanName);
	}

    public <T> void registerBean(@Nullable String beanName, Class<T> beanClass,
			@Nullable Supplier<T> supplier, BeanDefinitionCustomizer... customizers) {

		ClassDerivedBeanDefinition beanDefinition = new ClassDerivedBeanDefinition(beanClass);
		if (supplier != null) {
			beanDefinition.setInstanceSupplier(supplier);
		}
		for (BeanDefinitionCustomizer customizer : customizers) {
			customizer.customize(beanDefinition);
		}

		String nameToUse = (beanName != null ? beanName : beanClass.getName());
		registerBeanDefinition(nameToUse, beanDefinition);
	}
}
```

### 경량 IoC 컨테이너 직접 만들어 보기

```kotlin
interface BeanFactory {
    fun <T : Any> getBean(type: KClass<T>): T
    fun getBeanNamesForType(type: KClass<*>): Set<String>
}

interface BeanDefinitionRegistry {
    val beanDefinitionMap: Map<String, KClass<*>>
}

interface SingletonBeanRegistry {
    fun containsSingleton(beanName: String): Boolean
}


class BeanDefinitionOverrideException(
    beanName: String,
) : RuntimeException("Cannot register bean definition $beanName")

class NoSuchBeanDefinitionException(
    beanName: String,
) : RuntimeException("No bean named $beanName")

class NoUniqueBeanDefinitionException(
    beanName: String,
    foundBeanNames: Set<String>,
) : RuntimeException("No unique bean definition found for bean name '$beanName', found: $foundBeanNames")


class DefaultBeanFactory(
    vararg classes: KClass<*>,
) : BeanFactory,
    BeanDefinitionRegistry,
    SingletonBeanRegistry {

    private val singletonObjects = mutableMapOf<String, Any>()

    override val beanDefinitionMap: Map<String, KClass<*>> = buildMap {
        classes.forEach { type ->
            val beanName = type.simpleName!! // 간소화: 클래스 이름 그대로 빈 이름으로 사용
            if (beanName in this) throw BeanDefinitionOverrideException(beanName)
            put(beanName, type)
        }
    }

    /** 타입으로 빈을 찾는다. 인터페이스로 찾아도 되고, 처음 찾는 빈이면 만들어서 캐시에 넣어 둔다. */
    override fun <T : Any> getBean(type: KClass<T>): T {
        val beanName = type.simpleName!!
        val beanNames = getBeanNamesForType(type)
        if (beanNames.isEmpty()) throw NoSuchBeanDefinitionException(beanName)
        if (beanNames.size > 1) throw NoUniqueBeanDefinitionException(beanName, beanNames)

        val targetBeanName = beanNames.first()
        val bean = singletonObjects.getOrPut(targetBeanName) {
            createBean(targetBeanName)
        }
        return type.cast(bean)
    }

    /** 이 타입으로 꺼낼 수 있는 빈 이름을 모두 찾는다. */
    override fun getBeanNamesForType(type: KClass<*>): Set<String> {
        return beanDefinitionMap.filter { it.value.isSubclassOf(type) }.keys
    }

    /** 이미 만들어 둔 빈인지 확인한다. */
    override fun containsSingleton(beanName: String): Boolean {
        return singletonObjects.containsKey(beanName)
    }

    /** 등록된 빈을 전부 미리 만들어 둔다. */
    fun preInstantiateSingletons() {
        beanDefinitionMap.values.forEach { getBean(it) }
    }

    /** 주 생성자로 빈을 만든다. 생성자에 필요한 빈은 getBean으로 가져온다. */
    private fun createBean(beanName: String): Any {
        val constructor = beanDefinitionMap.getValue(beanName).primaryConstructor!!
        val arguments = constructor.parameters.map { getBean(it.type.classifier as KClass<*>) }
        return constructor.call(*arguments.toTypedArray())
    }
}
```

```kotlin
interface ApplicationContext : BeanFactory {
    fun refresh()
}

class GenericApplicationContext(
    vararg classes: KClass<*>,
) : ApplicationContext {

    val beanFactory: DefaultBeanFactory = DefaultBeanFactory(*classes)

    override fun <T : Any> getBean(type: KClass<T>): T {
        return this.beanFactory.getBean(type)
    }

    override fun getBeanNamesForType(type: KClass<*>): Set<String> {
        return this.beanFactory.getBeanNamesForType(type)
    }

    /** 빈을 미리 다 만들어 둔다. 실제 일은 beanFactory가 한다. */
    override fun refresh() {
        this.beanFactory.preInstantiateSingletons()
    }
}
```

### 실제 스프링에서는: refresh()부터 따라가기

```java
public abstract class AbstractApplicationContext extends DefaultResourceLoader
		implements ConfigurableApplicationContext {
	@Override
	public void refresh() throws BeansException, IllegalStateException {
		this.startupShutdownLock.lock();
		try {
			this.startupShutdownThread = Thread.currentThread();

			StartupStep contextRefresh = this.applicationStartup.start("spring.context.refresh");

			// Prepare this context for refreshing.
			prepareRefresh();

			// Tell the subclass to refresh the internal bean factory.
			ConfigurableListableBeanFactory beanFactory = obtainFreshBeanFactory();

			// Prepare the bean factory for use in this context.
			prepareBeanFactory(beanFactory);

			try {
				// Allows post-processing of the bean factory in context subclasses.
				postProcessBeanFactory(beanFactory);

				StartupStep beanPostProcess = this.applicationStartup.start("spring.context.beans.post-process");
				// Invoke factory processors registered as beans in the context.
				invokeBeanFactoryPostProcessors(beanFactory);
				// Register bean processors that intercept bean creation.
				registerBeanPostProcessors(beanFactory);
				beanPostProcess.end();

				// Initialize message source for this context.
				initMessageSource();

				// Initialize event multicaster for this context.
				initApplicationEventMulticaster();

				// Initialize other special beans in specific context subclasses.
				onRefresh();

				// Check for listener beans and register them.
				registerListeners();

				// Instantiate all remaining (non-lazy-init) singletons.
				finishBeanFactoryInitialization(beanFactory);

				// Last step: publish corresponding event.
				finishRefresh();
			}

			catch (RuntimeException | Error ex) {
				if (logger.isWarnEnabled()) {
					logger.warn("Exception encountered during context initialization - " +
							"cancelling refresh attempt: " + ex);
				}

				// Stop already started Lifecycle beans to avoid dangling resources.
				if (this.lifecycleProcessor != null && this.lifecycleProcessor.isRunning()) {
					try {
						this.lifecycleProcessor.stop();
					}
					catch (Throwable ex2) {
						logger.warn("Exception thrown from LifecycleProcessor on cancelled refresh", ex2);
					}
				}

				// Destroy already created singletons to avoid dangling resources.
				destroyBeans();

				// Reset 'active' flag.
				cancelRefresh(ex);

				// Propagate exception to caller.
				throw ex;
			}

			finally {
				contextRefresh.end();
			}
		}
		finally {
			this.startupShutdownThread = null;
			this.startupShutdownLock.unlock();
		}
	}
}
```

### 무엇을 만들지 모으기: 컴포넌트 스캔 → BeanDefinition

### 만들고 주입하기: getBean → createBean → 생성자 인자 해석

```java
public class DefaultListableBeanFactory extends AbstractAutowireCapableBeanFactory
		implements ConfigurableListableBeanFactory, BeanDefinitionRegistry, Serializable {
    ...

    @Override
	public <T> T getBean(Class<T> requiredType) throws BeansException {
		return getBean(requiredType, (Object[]) null);
	}

	@SuppressWarnings("unchecked")
	@Override
	public <T> T getBean(Class<T> requiredType, @Nullable Object @Nullable ... args) throws BeansException {
		Assert.notNull(requiredType, "Required type must not be null");
		Object resolved = resolveBean(ResolvableType.forRawClass(requiredType), args, false);
		if (resolved == null) {
			throw new NoSuchBeanDefinitionException(requiredType);
		}
		return (T) resolved;
	}
    ...
}
```

### 감싸기: initializeBean → BeanPostProcessor

### 다 만든 빈은 singletonObjects로

---

## 같은 인터페이스의 구현이 여럿일 때

### 후보 찾기

### 후보가 여럿일 때 고르는 순서

### List·Map으로 전부 받기

---

## 힙에서 확인하기

### 설계도와 실물: beanDefinitionMap · singletonObjects

### 스프링이 기록해 둔 의존 관계: dependentBeanMap

### List로 받은 빈

### @Configuration 클래스도 프록시다

### @Transactional 빈은 객체가 둘이다


---

## 참고
- https://docs.spring.io/spring-framework/reference/core/beans/introduction.html
- https://medium.com/@vkekukh/why-they-ask-whats-the-difference-between-ioc-and-dependency-injection-9cb1101c0a41
- 
- 